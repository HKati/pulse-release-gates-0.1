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
