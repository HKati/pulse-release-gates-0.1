from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"


def read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_pulse_ci_declares_attestation_permissions() -> None:
    text = read_workflow()

    assert "permissions:" in text
    assert "id-token: write" in text
    assert "attestations: write" in text
    assert "artifact-metadata: write" in text
    assert "contents: read" in text


def test_pulse_ci_attests_release_authority_artifact_binding_subject() -> None:
    text = read_workflow()

    assert 'Release authority artifact binding v0: attest' in text
    assert 'uses: actions/attest@v4.1.0' in text
    assert 'subject-path: ${{ env.PACK_DIR }}/artifacts/artifact_provenance_binding_v0.json' in text
    assert 'show-summary: true' in text


def test_pulse_ci_attestation_skips_pull_request_runs() -> None:
    text = read_workflow()

    assert "if: ${{ github.event_name != 'pull_request' }}" in text


def test_pulse_ci_attestation_step_order() -> None:
    text = read_workflow()

    materialize_idx = text.index(
        'Release authority artifact binding v0: materialize and verify'
    )
    attest_idx = text.index('Release authority artifact binding v0: attest')
    upload_idx = text.index('Upload release authority artifact binding v0')

    assert materialize_idx < attest_idx < upload_idx


def test_pulse_ci_attestation_step_is_standalone_workflow_step() -> None:
    text = read_workflow()

    for line in text.splitlines():
        if 'name: "Release authority artifact binding v0: attest"' in line:
            assert line.startswith("      - name:"), line
            return

    raise AssertionError("attestation step not found")
