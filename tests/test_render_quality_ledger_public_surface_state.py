import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.render_quality_ledger import write_quality_ledger  # noqa: E402


def render(status: dict) -> str:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        status_path = root / "status.json"
        out_path = root / "report_card.html"
        status_path.write_text(
            json.dumps(status, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_quality_ledger(status_path, out_path)
        return out_path.read_text(encoding="utf-8")


def base_prod_status() -> dict:
    return {
        "version": "1.0.0-prod",
        "created_utc": "2026-02-17T12:34:56Z",
        "metrics": {
            "run_mode": "prod",
            "required_gates": ["prod_gate_ok"],
        },
        "diagnostics": {
            "gates_stubbed": False,
            "scaffold": False,
        },
        "gates": {
            "prod_gate_ok": True,
            "detectors_materialized_ok": True,
            "external_summaries_present": True,
            "external_all_pass": True,
        },
    }


def test_clean_prod_surface_reports_materialized_reader_evidence_state() -> None:
    html = render(base_prod_status())

    assert "PROD-PASS" in html
    assert "PROD READER SURFACE — MATERIALIZED RELEASE-GRADE EVIDENCE STATE" in html
    assert "PROD MATERIALIZED RELEASE-GRADE SURFACE" not in html


def test_stubbed_prod_surface_keeps_reader_surface_without_materialized_wording() -> None:
    status = base_prod_status()
    status["metrics"]["gates_stubbed"] = True

    html = render(status)

    assert "PROD-PASS" in html
    assert "PROD READER SURFACE — MATERIALIZED RELEASE-GRADE EVIDENCE STATE" not in html
    assert "PROD READER SURFACE — STUBBED/SCAFFOLD EVIDENCE STATE" in html
    assert "STUBBED/SCAFFOLD" in html


def test_meta_diagnostics_stubbed_prod_surface_keeps_reader_surface() -> None:
    status = base_prod_status()
    status["meta"] = {"diagnostics": {"gates_stubbed": True}}

    html = render(status)

    assert "PROD-PASS" in html
    assert "PROD READER SURFACE — MATERIALIZED RELEASE-GRADE EVIDENCE STATE" not in html
    assert "PROD READER SURFACE — STUBBED/SCAFFOLD EVIDENCE STATE" in html
    assert "STUBBED/SCAFFOLD" in html


def test_prod_surface_requires_declared_policy_pass_before_materialized_wording() -> None:
    required_gate_fail = base_prod_status()
    required_gate_fail["gates"]["prod_gate_ok"] = False
    fail_html = render(required_gate_fail)

    assert "FAIL" in fail_html
    assert "PROD READER SURFACE — MATERIALIZED RELEASE-GRADE EVIDENCE STATE" not in fail_html

    unresolved = base_prod_status()
    unresolved["metrics"].pop("required_gates", None)
    unresolved_html = render(unresolved)

    assert "UNKNOWN" in unresolved_html
    assert (
        "PROD READER SURFACE — MATERIALIZED RELEASE-GRADE EVIDENCE STATE"
        not in unresolved_html
    )


def test_core_stubbed_surface_uses_positive_reader_state_wording() -> None:
    status = {
        "version": "1.0.0-core",
        "created_utc": "2026-02-17T12:34:56Z",
        "metrics": {
            "run_mode": "core",
            "required_gates": ["core_gate_ok"],
        },
        "diagnostics": {
            "gates_stubbed": True,
            "scaffold": True,
        },
        "gates": {
            "core_gate_ok": True,
            "detectors_materialized_ok": False,
        },
    }

    html = render(status)

    assert "STAGE-PASS" in html
    assert "CORE READER SURFACE" in html
    assert "STUBBED/SCAFFOLD" in html
    for bad in [
        "PUBLIC READER SURFACE — NON-NORMATIVE",
        "NON-RELEASE VIEW",
        "NOT RELEASE-GRADE",
        "Non-normative display surface",
        "It is not itself the release authority",
    ]:
        assert bad not in html

 
def test_prod_surface_blocks_materialized_wording_for_all_stub_scaffold_marker_paths() -> None:
    marker_cases = [
        (("diagnostics", "gates_stubbed"), True),
        (("diagnostics", "scaffold"), True),
        (("diagnostics", "stub_profile"), "stubbed"),
        (("metrics", "gates_stubbed"), True),
        (("metrics", "scaffold"), True),
        (("metrics", "stub_profile"), "stubbed"),
        (("meta", "diagnostics", "gates_stubbed"), True),
        (("meta", "diagnostics", "scaffold"), True),
        (("meta", "diagnostics", "stub_profile"), "stubbed"),
    ]

 
  def set_nested(obj: dict, path: tuple[str, ...], value: object) -> None:
        current = obj
        for key in path[:-1]:
            current = current.setdefault(key, {})
        current[path[-1]] = value

    for path, value in marker_cases:
        status = base_prod_status()
        set_nested(status, path, value)

        html = render(status)

        assert "PROD-PASS" in html
        assert (
            "PROD READER SURFACE — MATERIALIZED RELEASE-GRADE EVIDENCE STATE"
            not in html
        ), path
        assert "PROD READER SURFACE — STUBBED/SCAFFOLD EVIDENCE STATE" in html, path
