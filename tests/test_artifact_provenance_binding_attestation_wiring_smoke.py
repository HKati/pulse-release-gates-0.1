from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"
TOOLS_TESTS_LIST = REPO_ROOT / "ci" / "tools-tests.list"

ATTEST_SHA = "59d89421af93a897026c735860bf21b6eb4f7b26"
EXPECTED_ATTEST_IF = (
    "${{ github.event_name != 'pull_request' && needs.pulse.result == 'success' }}"
)


def read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def read_tools_tests_list() -> str:
    return TOOLS_TESTS_LIST.read_text(encoding="utf-8")


def top_level_job_blocks(text: str) -> dict[str, str]:
    starts: list[tuple[str, int]] = []
    offset = 0

    for line in text.splitlines(keepends=True):
        if line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            starts.append((line.strip()[:-1], offset))
        offset += len(line)

    blocks: dict[str, str] = {}
    for idx, (name, start) in enumerate(starts):
        end = starts[idx + 1][1] if idx + 1 < len(starts) else len(text)
        blocks[name] = text[start:end]

    return blocks


def workflow_blocks() -> tuple[str, str, dict[str, str]]:
    text = read_workflow()
    blocks = top_level_job_blocks(text)

    assert "pulse" in blocks
    assert "attest_release_authority_artifact_binding" in blocks
    assert "tools-tests" in blocks

    return blocks["pulse"], blocks["attest_release_authority_artifact_binding"], blocks


def job_field(job_block: str, field_name: str) -> str:
    prefix = f"    {field_name}:"
    for line in job_block.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    raise AssertionError(f"missing job field: {field_name}")


def test_pulse_job_remains_read_only_for_attestation_credentials() -> None:
    pulse_block, _attest_block, _blocks = workflow_blocks()

    assert "permissions:" in pulse_block
    assert "contents: read" in pulse_block

    assert "id-token: write" not in pulse_block
    assert "attestations: write" not in pulse_block
    assert "artifact-metadata: write" not in pulse_block


def test_attestation_job_declares_isolated_write_permissions() -> None:
    _pulse_block, attest_block, _blocks = workflow_blocks()

    assert "permissions:" in attest_block
    assert "contents: read" in attest_block
    assert "actions: read" in attest_block
    assert "id-token: write" in attest_block
    assert "attestations: write" in attest_block
    assert "artifact-metadata: write" in attest_block


def test_attestation_job_has_exact_combined_guard() -> None:
    _pulse_block, attest_block, _blocks = workflow_blocks()

    assert job_field(attest_block, "needs") == "pulse"
    assert job_field(attest_block, "if") == EXPECTED_ATTEST_IF


def test_attestation_job_downloads_uploaded_binding_artifact() -> None:
    _pulse_block, attest_block, _blocks = workflow_blocks()

    assert 'gh run download "${GITHUB_RUN_ID}"' in attest_block
    assert '--repo "${GITHUB_REPOSITORY}"' in attest_block
    assert '--name "release-authority-artifact-binding-v0"' in attest_block
    assert '--dir "attestation-subject"' in attest_block
    assert 'test -f "attestation-subject/artifact_provenance_binding_v0.json"' in attest_block
    assert 'sha256sum "attestation-subject/artifact_provenance_binding_v0.json"' in attest_block


def test_download_step_runs_before_attestation_action() -> None:
    _pulse_block, attest_block, _blocks = workflow_blocks()

    download_step_idx = attest_block.index(
        "- name: Download verified release authority artifact binding"
    )
    download_cmd_idx = attest_block.index('gh run download "${GITHUB_RUN_ID}"')
    repo_arg_idx = attest_block.index('--repo "${GITHUB_REPOSITORY}"')
    file_check_idx = attest_block.index(
        'test -f "attestation-subject/artifact_provenance_binding_v0.json"'
    )
    attest_step_idx = attest_block.index("- name: Attest release authority artifact binding v0")
    attest_action_idx = attest_block.index(f"uses: actions/attest@{ATTEST_SHA}")

    assert (
        download_step_idx
        < download_cmd_idx
        < repo_arg_idx
        < file_check_idx
        < attest_step_idx
        < attest_action_idx
    )


def test_attestation_action_is_pinned_to_immutable_sha() -> None:
    text = read_workflow()
    _pulse_block, attest_block, blocks = workflow_blocks()

    uses_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("uses: actions/attest@")
    ]

    assert uses_lines, "workflow must contain at least one actions/attest use"
    assert all(
        line == f"uses: actions/attest@{ATTEST_SHA}"
        for line in uses_lines
    ), uses_lines

    assert f"uses: actions/attest@{ATTEST_SHA}" in attest_block

    for job_name, block in blocks.items():
        if "uses: actions/attest@" in block:
            assert f"uses: actions/attest@{ATTEST_SHA}" in block, job_name

    assert "uses: actions/attest@v4.1.0" not in text
    assert "uses: actions/attest@v4" not in text


def test_attestation_subject_is_release_authority_binding_carrier() -> None:
    _pulse_block, attest_block, _blocks = workflow_blocks()

    assert "subject-path: attestation-subject/artifact_provenance_binding_v0.json" in attest_block
    assert "show-summary: true" in attest_block


def test_attestation_job_is_separate_job_between_pulse_and_tools_tests() -> None:
    text = read_workflow()

    pulse_idx = text.index("  pulse:")
    attest_idx = text.index("  attest_release_authority_artifact_binding:")
    tools_idx = text.index("  tools-tests:")

    assert pulse_idx < attest_idx < tools_idx


def test_binding_materialization_upload_precede_attestation_job() -> None:
    text = read_workflow()

    materialize_idx = text.index(
        'Release authority artifact binding v0: materialize and verify'
    )
    upload_idx = text.index("Upload release authority artifact binding v0")
    attest_job_idx = text.index("  attest_release_authority_artifact_binding:")

    assert materialize_idx < upload_idx < attest_job_idx


def test_inline_attestation_step_is_not_present_in_pulse_job() -> None:
    pulse_block, _attest_block, _blocks = workflow_blocks()

    assert 'Release authority artifact binding v0: attest' not in pulse_block
    assert "uses: actions/attest@" not in pulse_block


def test_attestation_smoke_is_registered_in_tools_manifest() -> None:
    manifest = read_tools_tests_list()

    assert "tests/test_artifact_provenance_binding_attestation_wiring_smoke.py" in manifest


def main() -> int:
    test_pulse_job_remains_read_only_for_attestation_credentials()
    test_attestation_job_declares_isolated_write_permissions()
    test_attestation_job_has_exact_combined_guard()
    test_attestation_job_downloads_uploaded_binding_artifact()
    test_download_step_runs_before_attestation_action()
    test_attestation_action_is_pinned_to_immutable_sha()
    test_attestation_subject_is_release_authority_binding_carrier()
    test_attestation_job_is_separate_job_between_pulse_and_tools_tests()
    test_binding_materialization_upload_precede_attestation_job()
    test_inline_attestation_step_is_not_present_in_pulse_job()
    test_attestation_smoke_is_registered_in_tools_manifest()
    print("artifact provenance binding attestation wiring smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
