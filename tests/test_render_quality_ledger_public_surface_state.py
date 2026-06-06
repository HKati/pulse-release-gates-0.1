import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.render_quality_ledger import write_quality_ledger  # noqa: E402


MATERIALIZED_PROD_SURFACE = (
    "PROD READER SURFACE — MATERIALIZED RELEASE-GRADE EVIDENCE STATE"
)
STUBBED_PROD_SURFACE = "PROD READER SURFACE — STUBBED/SCAFFOLD EVIDENCE STATE"
CORE_STUBBED_PUBLIC_BOUNDARY = (
    "CORE READER SURFACE — STUBBED/SCAFFOLD EVIDENCE STATE — "
    "NOT RELEASE-GRADE AUTHORITY"
)
PENDING_PROD_SURFACE = "PROD READER SURFACE — MATERIALIZATION PENDING"


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


def set_nested(obj: dict, path: tuple[str, ...], value: object) -> None:
    current = obj
    for key in path[:-1]:
        current = current.setdefault(key, {})
    current[path[-1]] = value


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
    assert MATERIALIZED_PROD_SURFACE in html
    assert "PROD MATERIALIZED RELEASE-GRADE SURFACE" not in html


def test_stubbed_prod_surface_keeps_reader_surface_without_materialized_wording() -> None:
    status = base_prod_status()
    status["metrics"]["gates_stubbed"] = True

    html = render(status)

    assert "PROD-PASS" in html
    assert MATERIALIZED_PROD_SURFACE not in html
    assert STUBBED_PROD_SURFACE in html
    assert "STUBBED/SCAFFOLD" in html


def test_meta_diagnostics_stubbed_prod_surface_keeps_reader_surface() -> None:
    status = base_prod_status()
    status["meta"] = {"diagnostics": {"gates_stubbed": True}}

    html = render(status)

    assert "PROD-PASS" in html
    assert MATERIALIZED_PROD_SURFACE not in html
    assert STUBBED_PROD_SURFACE in html
    assert "STUBBED/SCAFFOLD" in html


def test_prod_surface_requires_declared_policy_pass_before_materialized_wording() -> None:
    required_gate_fail = base_prod_status()
    required_gate_fail["gates"]["prod_gate_ok"] = False
    fail_html = render(required_gate_fail)

    assert "FAIL" in fail_html
    assert MATERIALIZED_PROD_SURFACE not in fail_html

    unresolved = base_prod_status()
    unresolved["metrics"].pop("required_gates", None)
    unresolved_html = render(unresolved)

    assert "UNKNOWN" in unresolved_html
    assert MATERIALIZED_PROD_SURFACE not in unresolved_html


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
    assert CORE_STUBBED_PUBLIC_BOUNDARY in html
    assert "declared-policy decision display: STAGE-PASS" in html
    assert html.index(CORE_STUBBED_PUBLIC_BOUNDARY) < html.index("STAGE-PASS")
    assert html.index(CORE_STUBBED_PUBLIC_BOUNDARY) < html.index("PASS")
    assert html.index(CORE_STUBBED_PUBLIC_BOUNDARY) < html.index(
        "declared-policy decision display: STAGE-PASS"
    )
    for bad in [
        "PUBLIC READER SURFACE — NON-NORMATIVE",
        "NON-RELEASE VIEW",
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

    for path, value in marker_cases:
        status = base_prod_status()
        set_nested(status, path, value)

        html = render(status)

        assert "PROD-PASS" in html
        assert MATERIALIZED_PROD_SURFACE not in html, path
        assert STUBBED_PROD_SURFACE in html, path


def test_prod_surface_keeps_pending_wording_for_neutral_stub_profiles() -> None:
    neutral_cases = [
        (("diagnostics", "stub_profile"), ""),
        (("diagnostics", "stub_profile"), "none"),
        (("diagnostics", "stub_profile"), "false"),
        (("diagnostics", "stub_profile"), "real"),
        (("diagnostics", "stub_profile"), "not_stubbed"),
        (("metrics", "stub_profile"), "real"),
        (("metrics", "stub_profile"), "not_stubbed"),
        (("meta", "diagnostics", "stub_profile"), "real"),
        (("meta", "diagnostics", "stub_profile"), "not_stubbed"),
    ]

    for path, value in neutral_cases:
        status = base_prod_status()
        status["gates"]["detectors_materialized_ok"] = False
        set_nested(status, path, value)

        html = render(status)

        assert "PROD-PASS" in html
        assert PENDING_PROD_SURFACE in html, path
        assert STUBBED_PROD_SURFACE not in html, path
        assert MATERIALIZED_PROD_SURFACE not in html, path


def test_terminology_risk_register_has_no_conflict_remnants() -> None:
    text = (REPO_ROOT / "docs" / "PULSE_TERMINOLOGY_RISK_REGISTER_v0.md").read_text(
        encoding="utf-8"
    )

    assert "HKati-patch" not in text
    assert "=======" not in text
    assert "\nmain\n" not in text
    assert text.count("| release-grade lane eligibility |") == 1
    assert text.count("| external evidence presence |") == 1
    assert text.count("| publication exposure |") == 1
    assert text.count("| third-party integration / adoption |") == 1
    assert text.count("| hardening layer |") == 1
