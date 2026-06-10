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


def test_release_authority_manifest_trace_carrier_dependency_is_documented_and_wired() -> None:
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[1]

    workflow = (
        repo_root / ".github" / "workflows" / "pulse_ci.yml"
    ).read_text(encoding="utf-8")

    manifest_doc_path = repo_root / "docs" / "release_authority_manifest_v0.md"
    checklist_path = (
        repo_root / "docs" / "PULSE_REVIEWABLE_MECHANICS_CHECKLIST_v0.md"
    )

    assert manifest_doc_path.is_file()
    assert checklist_path.is_file()

    manifest_doc = manifest_doc_path.read_text(encoding="utf-8")
    checklist_doc = checklist_path.read_text(encoding="utf-8")

    # Workflow wiring: artifact-provenance binding intentionally consumes the
    # release authority manifest as a trace-carrier input.
    assert "Release authority artifact binding v0: materialize and verify" in workflow
    assert "build_artifact_provenance_binding_v0.py" in workflow
    assert "verify_artifact_provenance_binding_v0.py" in workflow
    assert "--release-authority-manifest" in workflow
    assert "release_authority_v0.json" in workflow

    # Release authority manifest docs: required trace-carrier dependency is
    # classified without turning the sidecar into a decision engine.
    assert "Trace-carrier dependency boundary" in manifest_doc
    assert (
        "When artifact-provenance binding is enabled, "
        "`release_authority_v0.json` may be required as a trace-carrier input "
        "for the provenance-binding layer."
    ) in manifest_doc
    assert (
        "A required trace carrier can make the provenance-binding layer fail "
        "if the carrier is missing."
    ) in manifest_doc
    assert (
        "That trace-carrier requirement does not make "
        "`release_authority_v0.json` a second decision engine."
    ) in manifest_doc
    assert "trace-carrier required for provenance binding" in manifest_doc
    assert "≠ release authority" in manifest_doc
    assert "≠ primary allow/block decision" in manifest_doc
    assert "≠ gate materialization" in manifest_doc
    assert "≠ second decision engine" in manifest_doc

    # Reviewable mechanics checklist: the same dependency is recorded as a
    # review boundary, not as release-authority promotion.
    assert "Trace-carrier dependency" in checklist_doc
    assert (
        "An audit sidecar may be required by a later provenance-binding layer "
        "as a trace carrier."
    ) in checklist_doc
    assert (
        "That requirement must not be confused with release authority."
    ) in checklist_doc
    assert (
        "A required trace carrier can make the provenance-binding layer fail "
        "if the carrier is missing, but it must not replace the primary "
        "artifact-bound release-authority path."
    ) in checklist_doc
