from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"

ATTEST_SHA = "59d89421af93a897026c735860bf21b6eb4f7b26"


def read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def workflow_blocks() -> tuple[str, str]:
    text = read_workflow()

    pulse_idx = text.index("  pulse:")
    attest_idx = text.index("  attest_release_authority_artifact_binding:")
    tools_idx = text.index("  tools-tests:")

    return text[pulse_idx:attest_idx], text[attest_idx:tools_idx]


def test_pulse_job_remains_read_only_for_attestation_credentials() -> None:
    pulse_block, _attest_block = workflow_blocks()

    assert "permissions:" in pulse_block
    assert "contents: read" in pulse_block

    assert "id-token: write" not in pulse_block
    assert "attestations: write" not in pulse_block
    assert "artifact-metadata: write" not in pulse_block


def test_attestation_job_declares_isolated_write_permissions() -> None:
    _pulse_block, attest_block = workflow_blocks()

    assert "permissions:" in attest_block
    assert "contents: read" in attest_block
    assert "actions: read" in attest_block
    assert "id-token: write" in attest_block
    assert "attestations: write" in attest_block
    assert "artifact-metadata: write" in attest_block


def test_attestation_job_depends_on_verified_pulse_job() -> None:
    _pulse_block, attest_block = workflow_blocks()

    assert "needs: pulse" in attest_block
    assert "github.event_name != 'pull_request'" in attest_block
    assert "needs.pulse.result == 'success'" in attest_block


def test_attestation_job_downloads_uploaded_binding_artifact() -> None:
    _pulse_block, attest_block = workflow_blocks()

    assert 'gh run download "${GITHUB_RUN_ID}"' in attest_block
    assert '--name "release-authority-artifact-binding-v0"' in attest_block
    assert '--dir "attestation-subject"' in attest_block
    assert 'test -f "attestation-subject/artifact_provenance_binding_v0.json"' in attest_block
    assert 'sha256sum "attestation-subject/artifact_provenance_binding_v0.json"' in attest_block


def test_attestation_action_is_pinned_to_immutable_sha() -> None:
    text = read_workflow()
    _pulse_block, attest_block = workflow_blocks()

    uses_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("uses: actions/attest@")
    ]

    assert uses_lines == [f"uses: actions/attest@{ATTEST_SHA}"]
    assert f"uses: actions/attest@{ATTEST_SHA}" in attest_block

    assert "uses: actions/attest@v4.1.0" not in text
    assert "uses: actions/attest@v4" not in text


def test_attestation_subject_is_release_authority_binding_carrier() -> None:
    _pulse_block, attest_block = workflow_blocks()

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
    pulse_block, _attest_block = workflow_blocks()

    assert 'Release authority artifact binding v0: attest' not in pulse_block
    assert "uses: actions/attest@" not in pulse_block
