from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pulse_ci.yml"


def read_workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_pulse_ci_materializes_and_verifies_artifact_provenance_binding() -> None:
    text = read_workflow()

    assert "Release authority artifact binding v0: materialize and verify" in text
    assert "build_artifact_provenance_binding_v0.py" in text
    assert "verify_artifact_provenance_binding_v0.py" in text
    assert "artifact_provenance_binding_v0.json" in text


def test_pulse_ci_binding_uses_workflow_effective_policy_sets() -> None:
    text = read_workflow()

    assert 'POLICY_ARGS=(--policy-set "${PULSE_POLICY_SET:-core_required}")' in text
    assert 'POLICY_ARGS+=(--policy-set release_required)' in text
    assert 'if [[ "${PULSE_IS_RELEASE:-0}" == "1" ]]; then' in text


def test_pulse_ci_uploads_artifact_provenance_binding() -> None:
    text = read_workflow()

    assert "Upload release authority artifact binding v0" in text
    assert "release-authority-artifact-binding-v0" in text
    assert "${{ env.PACK_DIR }}/artifacts/artifact_provenance_binding_v0.json" in text


def test_pulse_ci_binding_step_is_after_release_decision_materialization() -> None:
    text = read_workflow()

    release_decision_idx = text.index('Release decision v0: materialize artifact')
    binding_idx = text.index('Release authority artifact binding v0: materialize and verify')

    assert release_decision_idx < binding_idx
