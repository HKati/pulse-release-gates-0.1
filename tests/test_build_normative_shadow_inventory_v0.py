import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "build_normative_shadow_inventory_v0.py"


def run_builder(tmp_path: Path) -> tuple[dict, str]:
    out_json = tmp_path / "normative_shadow_inventory_v0.json"
    out_md = tmp_path / "normative_shadow_inventory_v0.md"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(REPO_ROOT),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        check=True,
    )

    return json.loads(out_json.read_text(encoding="utf-8")), out_md.read_text(
        encoding="utf-8"
    )


def entry_by_path(inventory: dict, path: str) -> dict:
    for item in inventory["entries"]:
        if item["path"] == path:
            return item
    raise AssertionError(f"missing inventory entry: {path}")


def test_inventory_builder_outputs_json_and_markdown(tmp_path: Path) -> None:
    inventory, markdown = run_builder(tmp_path)

    assert inventory["schema_id"] == "pulse.normative_shadow_inventory.v0"
    assert inventory["schema_version"] == "0.1.0"
    assert inventory["entry_count"] == len(inventory["entries"])
    assert "Normative vs Shadow Inventory Report v0" in markdown


def test_inventory_classifies_pulse_ci_as_authority_workflow(tmp_path: Path) -> None:
    inventory, _markdown = run_builder(tmp_path)

    pulse_ci = entry_by_path(inventory, ".github/workflows/pulse_ci.yml")

    assert pulse_ci["carrier_class"] == "authority"
    assert pulse_ci["authority_impacting"] == "yes"
    assert pulse_ci["release_path_participation"] is True
    assert pulse_ci["required_gate_participation"] is True


def test_inventory_classifies_current_run_export_candidate_as_non_active_shadow(
    tmp_path: Path,
) -> None:
    inventory, _markdown = run_builder(tmp_path)
    workflow_path = (
        ".github/workflows/"
        "pulsemech_compute_current_run_export_candidate.yml"
    )
    candidate = entry_by_path(inventory, workflow_path)

    assert candidate["primary_role"] == (
        "non-active current-run compute candidate workflow"
    )
    assert candidate["carrier_class"] == "diagnostic_shadow"
    assert candidate["authority_impacting"] == "conditional"
    assert candidate["required_gate_participation"] is False
    assert candidate["attestation_participation"] is False
    assert candidate["release_path_participation"] is False
    assert "candidate-only" in candidate["authority_boundary"]
    assert "pre-authority" in candidate["authority_boundary"]
    assert "declared required gate" in candidate["authority_boundary"]
    assert "selected successful same-repository PULSE CI source run" in candidate[
        "reads_artifacts"
    ]
    assert "deterministic finalized current-run carrier" in candidate[
        "writes_artifacts"
    ]
    assert candidate["publishes_artifacts"] == [
        "candidate-only GitHub Actions artifact bundle"
    ]
    assert not [
        finding
        for finding in inventory["drift_findings"]
        if finding["path"] == workflow_path
    ]


def test_inventory_classifies_current_run_artifact_observed_candidate_as_non_active_shadow(
    tmp_path: Path,
) -> None:
    inventory, _markdown = run_builder(tmp_path)
    workflow_path = (
        ".github/workflows/"
        "pulsemech_compute_current_run_artifact_observed_candidate.yml"
    )
    candidate = entry_by_path(inventory, workflow_path)

    assert candidate["primary_role"] == (
        "current-run artifact-observed compute proof workflow"
    )
    assert candidate["carrier_class"] == "diagnostic_shadow"
    assert candidate["authority_impacting"] == "conditional"
    assert candidate["required_gate_participation"] is False
    assert candidate["attestation_participation"] is False
    assert candidate["release_path_participation"] is False

    authority_boundary = candidate["authority_boundary"]
    assert "Manual candidate-only" in authority_boundary
    assert "non-active" in authority_boundary
    assert "artifact-observed" in authority_boundary
    assert "pre-authority" in authority_boundary
    assert "recorded evidence" in authority_boundary
    assert "separate declared required gate" in authority_boundary

    assert candidate["reads_artifacts"] == [
        "selected successful same-repository Step 3F provider workflow run",
        "exact Step 3F current-run export candidate artifact",
        "verified current-run candidate-bundle intake",
        "exact current-run subject and protected control-plane components",
        (
            "finalized carrier, observed expectation, observed subject-input "
            "packet, policy, gate registry, schemas, and verifier inputs"
        ),
    ]
    assert candidate["writes_artifacts"] == [
        "artifact-observed compute-binding report",
        "deterministic current-run integration plan",
        "planned-observed relation",
        "candidate materializer report",
        "separate folded candidate status",
        "artifact-observed proof manifest and checksum-bound proof directory",
    ]
    assert candidate["publishes_artifacts"] == [
        "candidate-only artifact-observed GitHub Actions proof bundle"
    ]

    notes = candidate["notes"]
    for state in ("false", "missing", "partial", "unresolved"):
        assert state in notes
    for prohibited_effect in (
        "activating a gate",
        "compute budget",
        "runtime observation",
        "release decision",
        "release authority",
    ):
        assert prohibited_effect in notes

    assert not [
        finding
        for finding in inventory["drift_findings"]
        if finding["path"] == workflow_path
    ]


def test_inventory_classifies_bounded_execution_reference_as_non_active_shadow(
    tmp_path: Path,
) -> None:
    inventory, markdown = run_builder(tmp_path)
    workflow_path = (
        ".github/workflows/"
        "pulsemech_compute_bounded_execution_reference.yml"
    )
    reference = entry_by_path(inventory, workflow_path)

    assert reference["primary_role"] == (
        "non-active bounded-execution reference workflow"
    )
    assert reference["carrier_class"] == "diagnostic_shadow"
    assert reference["authority_impacting"] == "conditional"
    assert reference["required_gate_participation"] is False
    assert reference["attestation_participation"] is False
    assert reference["release_path_participation"] is False

    for boundary in (
        "Manual candidate-only",
        "non-active",
        "pre-authority",
        "controlled reference inputs",
        "not the primary production release path",
        "recorded evidence",
        "separate declared required gate",
    ):
        assert boundary in reference["authority_boundary"]

    assert reference["reads_artifacts"] == [
        "exact reviewed main source commit and protected control-plane sources",
        "exact repository, workflow, run, attempt, and checkout context",
        "ordered core_required policy output and gate registry",
        "prelaunch specification and controlled status/pending-state inputs",
        "plan-only integration request, component manifest, and plan",
    ]
    assert reference["writes_artifacts"] == [
        "prelaunch expectations and prepared source/input carrier",
        "bounded capture of three checker and three consumer processes",
        "bounded-reference subject-input packet and partial runtime packet",
        "artifact-only baseline and separate runtime-bound compute report",
        "planned-observed relation and separate non-active candidate state",
        "byte-identical reconstruction archives from two separate processes",
        "checksum-closed reference_capsule_v0.zip",
    ]
    assert reference["publishes_artifacts"] == [
        "non-active bounded-reference GitHub Actions artifact bundle"
    ]
    for note in (
        "Checker exits 0/1/2",
        "consumer ready/held",
        "not production release decisions or deployment admission",
        "Whole-packet coverage stays partial",
        "resources unavailable",
        "does not establish acquisition provenance",
        "observed-reference acceptance",
        "full Step 5 closure",
        "No resource measurement",
        "compute budget",
        "gate activation",
        "policy promotion",
        "authority_effect = none",
        "same_run_release_authority_eligible = false",
        "active_gate_eligible = false",
    ):
        assert note in reference["notes"]
    assert workflow_path in markdown
    assert not [
        finding
        for finding in inventory["drift_findings"]
        if finding["path"] == workflow_path
    ]


def test_inventory_classifies_whole_runtime_observation_reference_as_non_active_shadow(
    tmp_path: Path,
) -> None:
    inventory, markdown = run_builder(tmp_path)
    workflow_path = (
        ".github/workflows/"
        "pulsemech_compute_whole_runtime_observation_reference.yml"
    )
    reference = entry_by_path(inventory, workflow_path)

    assert reference["primary_role"] == (
        "non-active current-run whole-runtime observation reference workflow"
    )
    assert reference["carrier_class"] == "diagnostic_shadow"
    assert reference["authority_impacting"] == "conditional"
    assert reference["required_gate_participation"] is False
    assert reference["attestation_participation"] is False
    assert reference["release_path_participation"] is False

    for boundary in (
        "Manual owner-dispatched",
        "non-active observation and preservation workflow",
        "one exact PULSE CI subject",
        "one exact Step 3F provider",
        "outside subject totals",
        "neither participates in nor changes",
        "subject's existing release decision",
        "recorded evidence",
        "separate declared required gate",
    ):
        assert boundary in reference["authority_boundary"]

    assert reference["reads_artifacts"] == [
        (
            "exact reviewed main source commit and protected "
            "control-plane sources"
        ),
        (
            "independently validated Step 5C prelaunch plan and exact "
            "plan digest"
        ),
        (
            "one exact attempt-1 PULSE CI subject run and complete "
            "job/step metadata"
        ),
        (
            "selected exact subject terminal artifacts and their "
            "GitHub SHA-256 bindings"
        ),
        (
            "one exact attempt-1 Step 3F provider run and current-run "
            "candidate envelope"
        ),
        (
            "exact reference-workflow context and cross-job handoff "
            "bindings"
        ),
    ]

    assert reference["writes_artifacts"] == [
        "deterministic prepared Step 5C input carrier",
        "exact capture carrier without a verifier verdict",
        (
            "generic partial runtime-observation packet and existing-core "
            "derived outputs"
        ),
        "two byte-identical deterministic reconstruction archives",
        "verification_record_v0.json and SHA256SUMS",
        "checksum-closed reference_capsule_v0.zip",
    ]

    assert reference["publishes_artifacts"] == [
        "exact non-active verification-input handoff artifact",
        "verified non-active whole-runtime reference capsule artifact",
    ]

    for note in (
        "not host-wide tracing",
        "I and E may become complete only after independent verification",
        "R stays partial",
        "C stays not complete",
        "M stays unavailable",
        "generic runtime coverage stays partial",
        "outside subject totals",
        "does not alter the subject decision",
        "authority_effect = none",
        "same_run_release_authority_eligible = false",
        "active_gate_eligible = false",
    ):
        assert note in reference["notes"]

    assert workflow_path in markdown
    assert not [
        finding
        for finding in inventory["drift_findings"]
        if finding["path"] == workflow_path
    ]


def test_inventory_does_not_classify_renamed_bounded_reference_copies(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    workflow_name = "pulsemech_compute_bounded_execution_reference.yml"
    original = (REPO_ROOT / ".github" / "workflows" / workflow_name).read_bytes()
    # Identical contents and display names do not extend the exact-path entry.
    alternate_names = (
        "pulsemech_compute_bounded_execution_reference_copy.yml",
        "pulsemech_compute_bounded_execution_reference.yaml",
        "Pulsemech_compute_bounded_execution_reference.yml",
    )
    for filename in alternate_names:
        (workflows / filename).write_bytes(original)

    inventory = run_builder_for_repo(repo, tmp_path)
    expected_paths = {".github/workflows/" + name for name in alternate_names}
    for path in expected_paths:
        assert entry_by_path(inventory, path)["primary_role"] == (
            "unclassified workflow"
        )
    assert {finding["path"] for finding in inventory["drift_findings"]} == expected_paths
    assert len(inventory["drift_findings"]) == len(expected_paths)
    for finding in inventory["drift_findings"]:
        assert finding["severity"] == "warning"
        assert finding["finding"] == (
            "workflow requires explicit carrier-role classification"
        )


def test_inventory_keeps_unknown_workflow_drift_beside_bounded_reference(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    workflow_name = "pulsemech_compute_bounded_execution_reference.yml"
    (workflows / workflow_name).write_bytes(
        (REPO_ROOT / ".github" / "workflows" / workflow_name).read_bytes()
    )
    write_workflow(workflows / "unclassified_future_task.yml", name="Future task")

    inventory = run_builder_for_repo(repo, tmp_path)
    assert entry_by_path(inventory, ".github/workflows/" + workflow_name)[
        "primary_role"
    ] == "non-active bounded-execution reference workflow"
    assert inventory["drift_findings"] == [
        {
            "severity": "warning",
            "path": ".github/workflows/unclassified_future_task.yml",
            "finding": "workflow requires explicit carrier-role classification",
        }
    ]


def test_inventory_classifies_device_ledger_swift_as_non_authorizing_advisory(
    tmp_path: Path,
) -> None:
    inventory, _markdown = run_builder(tmp_path)
    workflow_path = ".github/workflows/pulsemech_ledger_swift.yml"
    workflow = entry_by_path(inventory, workflow_path)

    assert workflow["primary_role"] == (
        "device-ledger Swift implementation verification workflow"
    )
    assert workflow["carrier_class"] == "advisory"
    assert workflow["authority_impacting"] == "no"
    assert workflow["required_gate_participation"] is False
    assert workflow["attestation_participation"] is False
    assert workflow["release_path_participation"] is False
    assert workflow["publishes_artifacts"] == []

    assert "repository verification signals only" in workflow[
        "authority_boundary"
    ]
    assert "not recorded device-observation evidence" in workflow[
        "authority_boundary"
    ]
    assert "No real iPhone observation" in workflow["notes"]
    assert "authority effect" in workflow["notes"]

    assert not [
        finding
        for finding in inventory["drift_findings"]
        if finding["path"] == workflow_path
    ]


def test_inventory_classifies_check_gates_as_enforcement_carrier(tmp_path: Path) -> None:
    inventory, _markdown = run_builder(tmp_path)

    check_gates = entry_by_path(inventory, "PULSE_safe_pack_v0/tools/check_gates.py")

    assert check_gates["carrier_class"] == "enforcement"
    assert check_gates["authority_impacting"] == "yes"
    assert "literal true-only" in check_gates["authority_boundary"]


def test_inventory_classifies_quality_ledger_as_reader_carrier(tmp_path: Path) -> None:
    inventory, _markdown = run_builder(tmp_path)

    ledger = entry_by_path(inventory, "PULSE_safe_pack_v0/tools/render_quality_ledger.py")

    assert ledger["carrier_class"] == "reader"
    assert ledger["authority_impacting"] == "conditional"
    assert "Non-authorizing carrier" in ledger["authority_boundary"]


def test_inventory_includes_binding_and_verifier_carriers(tmp_path: Path) -> None:
    inventory, _markdown = run_builder(tmp_path)

    builder = entry_by_path(
        inventory,
        "PULSE_safe_pack_v0/tools/build_artifact_provenance_binding_v0.py",
    )
    verifier = entry_by_path(
        inventory,
        "PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py",
    )

    assert builder["carrier_class"] == "binding"
    assert verifier["carrier_class"] == "binding"
    assert builder["authority_impacting"] == "yes"
    assert verifier["authority_impacting"] == "yes"


def test_inventory_markdown_contains_authority_carrier_and_drift_section(
    tmp_path: Path,
) -> None:
    _inventory, markdown = run_builder(tmp_path)

    assert "status.json -> declared gate policy" in markdown
    assert "## Drift findings" in markdown


def run_builder_for_repo(repo_root: Path, tmp_path: Path) -> dict:
    out_json = tmp_path / "normative_shadow_inventory_v0.json"
    out_md = tmp_path / "normative_shadow_inventory_v0.md"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(repo_root),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        check=True,
    )

    return json.loads(out_json.read_text(encoding="utf-8"))


def write_workflow(path: Path, *, name: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"name: {name}",
                "",
                "on:",
                "  pull_request:",
                "",
                "jobs:",
                "  check:",
                "    runs-on: ubuntu-latest",
                "    steps:",
                "      - name: Example",
                "        run: |",
                "          echo ok",
                *body.splitlines(),
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_inventory_classifies_core_baseline_workflows_without_false_drift(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    write_workflow(
        repo / ".github" / "workflows" / "core_baseline_capture.yml",
        name="Core Baseline Capture",
    )
    write_workflow(
        repo / ".github" / "workflows" / "core_baseline_check.yml",
        name="Core Baseline Check",
    )

    inventory = run_builder_for_repo(repo, tmp_path)

    capture = entry_by_path(inventory, ".github/workflows/core_baseline_capture.yml")
    check = entry_by_path(inventory, ".github/workflows/core_baseline_check.yml")

    assert capture["primary_role"] == "core baseline workflow"
    assert capture["carrier_class"] == "advisory"
    assert check["primary_role"] == "core baseline workflow"
    assert check["carrier_class"] == "advisory"
    assert inventory["drift_findings"] == []


def test_inventory_does_not_classify_publish_mentions_as_publication(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    write_workflow(
        repo / ".github" / "workflows" / "release_check.yml",
        name="Release Check",
        body="          echo 'nothing to publish in this release check'",
    )
    write_workflow(
        repo / ".github" / "workflows" / "theory_overlay_v0.yml",
        name="Theory Overlay v0",
        body="          echo 'nothing to publish for this overlay'",
    )

    inventory = run_builder_for_repo(repo, tmp_path)

    release_check = entry_by_path(inventory, ".github/workflows/release_check.yml")
    theory_overlay = entry_by_path(inventory, ".github/workflows/theory_overlay_v0.yml")

    assert release_check["carrier_class"] == "advisory"
    assert release_check["primary_role"] == "release check workflow"

    assert theory_overlay["carrier_class"] == "diagnostic_shadow"
    assert theory_overlay["primary_role"] == "diagnostic / overlay workflow"


def test_inventory_includes_release_decision_materializer_when_present(
    tmp_path: Path,
) -> None:
    inventory, _markdown = run_builder(tmp_path)

    materializer = entry_by_path(
        inventory,
        "PULSE_safe_pack_v0/tools/materialize_release_decision.py",
    )

    assert materializer["primary_role"] == "release-decision materialization"
    assert materializer["carrier_class"] == "authority"
    assert materializer["authority_impacting"] == "yes"
    assert "release-decision labels" in materializer["authority_boundary"]


def test_inventory_has_no_unclassified_workflow_drift_for_current_repo(
    tmp_path: Path,
) -> None:
    inventory, _markdown = run_builder(tmp_path)

    unclassified = [
        finding
        for finding in inventory["drift_findings"]
        if finding["finding"] == "workflow requires explicit carrier-role classification"
    ]

    assert unclassified == []


def test_inventory_classifies_validate_status_as_status_contract_carrier(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    write_workflow(
        repo / ".github" / "workflows" / "validate-status.yml",
        name="Validate Status",
    )

    inventory = run_builder_for_repo(repo, tmp_path)

    validate_status = entry_by_path(inventory, ".github/workflows/validate-status.yml")

    assert validate_status["primary_role"] == "status validation workflow"
    assert validate_status["carrier_class"] == "status_contract"
    assert validate_status["authority_impacting"] == "conditional"
    assert inventory["drift_findings"] == []


def test_inventory_classifies_public_surface_audit_as_audit_carrier(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    write_workflow(
        repo / ".github" / "workflows" / "public_surface_audit.yml",
        name="Public Surface Audit",
    )

    inventory = run_builder_for_repo(repo, tmp_path)

    audit = entry_by_path(inventory, ".github/workflows/public_surface_audit.yml")

    assert audit["primary_role"] == "public surface audit workflow"
    assert audit["carrier_class"] == "audit_preservation"
    assert audit["authority_impacting"] == "no"
    assert inventory["drift_findings"] == []


def test_inventory_classifies_security_and_hygiene_workflows_without_drift(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    write_workflow(repo / ".github" / "workflows" / "dco.yml", name="DCO Check")
    write_workflow(
        repo / ".github" / "workflows" / "workflow_lint.yml",
        name="workflow-lint",
    )
    write_workflow(repo / ".github" / "workflows" / "gitleaks.yml", name="Gitleaks")
    write_workflow(
        repo / ".github" / "workflows" / "upload_sarif.yml",
        name="Upload SARIF",
    )

    inventory = run_builder_for_repo(repo, tmp_path)

    assert entry_by_path(inventory, ".github/workflows/dco.yml")["carrier_class"] == "advisory"
    assert entry_by_path(inventory, ".github/workflows/workflow_lint.yml")["carrier_class"] == "advisory"
    assert entry_by_path(inventory, ".github/workflows/gitleaks.yml")["carrier_class"] == "advisory"
    assert entry_by_path(inventory, ".github/workflows/upload_sarif.yml")["carrier_class"] == "advisory"
    assert inventory["drift_findings"] == []


def test_inventory_classifies_publication_workflows_without_body_publish_false_positive(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    write_workflow(
        repo / ".github" / "workflows" / "publish_report_pages.yml",
        name="Publish Report Pages",
    )
    write_workflow(
        repo / ".github" / "workflows" / "cancel_pages_deployment.yml",
        name="Cancel Pages Deployment",
    )

    inventory = run_builder_for_repo(repo, tmp_path)

    publish = entry_by_path(inventory, ".github/workflows/publish_report_pages.yml")
    cancel = entry_by_path(inventory, ".github/workflows/cancel_pages_deployment.yml")

    assert publish["carrier_class"] == "publication"
    assert publish["authority_impacting"] == "no"
    assert cancel["carrier_class"] == "publication"
    assert cancel["authority_impacting"] == "no"
    assert inventory["drift_findings"] == []


def test_inventory_classifies_shadow_and_overlay_workflows_without_drift(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    write_workflow(
        repo / ".github" / "workflows" / "theory_overlay_v0.yml",
        name="Theory Overlay v0",
        body="          echo 'nothing to publish for this overlay'",
    )
    write_workflow(
        repo / ".github" / "workflows" / "parameter_golf_shadow.yml",
        name="Parameter Golf Shadow",
    )
    write_workflow(
        repo / ".github" / "workflows" / "pulse_topology_demo.yml",
        name="Pulse Topology Demo",
    )

    inventory = run_builder_for_repo(repo, tmp_path)

    overlay = entry_by_path(inventory, ".github/workflows/theory_overlay_v0.yml")
    parameter_golf = entry_by_path(
        inventory,
        ".github/workflows/parameter_golf_shadow.yml",
    )
    topology = entry_by_path(inventory, ".github/workflows/pulse_topology_demo.yml")

    assert overlay["carrier_class"] == "diagnostic_shadow"
    assert parameter_golf["carrier_class"] == "diagnostic_shadow"
    assert topology["carrier_class"] == "diagnostic_shadow"
    assert inventory["drift_findings"] == []


def test_inventory_classifies_pulse_pd_smoke_without_drift(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    write_workflow(
        repo / ".github" / "workflows" / "pulse_pd_smoke.yml",
        name="PULSE PD Smoke",
    )

    inventory = run_builder_for_repo(repo, tmp_path)

    pulse_pd = entry_by_path(inventory, ".github/workflows/pulse_pd_smoke.yml")

    assert pulse_pd["carrier_class"] == "diagnostic_shadow"
    assert pulse_pd["primary_role"] == "diagnostic / shadow workflow"
    assert pulse_pd["authority_impacting"] == "conditional"
    assert inventory["drift_findings"] == []
