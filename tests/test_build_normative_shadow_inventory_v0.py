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
