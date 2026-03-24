import json
import sys
from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.render_quality_ledger import (  # noqa: E402
    decision_from_status,
    write_quality_ledger,
)


CORE_REQUIRED_GATES = [
    "pass_controls_refusal",
    "pass_controls_sanit",
    "sanitization_effective",
    "q1_grounded_ok",
    "q4_slo_ok",
]


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def base_status() -> dict:
    return {
        "version": "1.0.0-core",
        "created_utc": "2026-02-17T12:34:56Z",
        "metrics": {
            "run_mode": "core",
            "RDSI": 0.93,
            "required_gates": list(CORE_REQUIRED_GATES),
        },
        "gates": {
            "pass_controls_refusal": True,
            "pass_controls_sanit": True,
            "sanitization_effective": True,
            "q1_grounded_ok": True,
            "q4_slo_ok": True,
        },
    }


def render_html(status_path: Path, out_path: Path, status: dict) -> str:
    write_json(status_path, status)
    write_quality_ledger(status_path, out_path)
    return read_text(out_path)


def assert_decision_badge(html: str, *, label: str, badge_class: str) -> None:
    expected = f'<div class="badge {badge_class}">{escape(label)}</div>'
    assert html.count('class="badge ') == 1
    assert expected in html


def test_external_detectors_section_renders_summary_and_detector_rows(
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"

    status = base_status()
    status["gates"]["external_all_pass"] = False
    status["external"] = {
        "all_pass": False,
        "summaries_present": True,
        "summary_count": 2,
        "metrics": [
            {"name": "promptfoo", "value": 0.91, "threshold": 0.95, "pass": False},
            {"name": "llamaguard", "value": 0.99, "threshold": 0.95, "pass": True},
        ],
    }

    assert decision_from_status(status, status_path=status_path) == (
        "STAGE-PASS",
        "badge-pass",
    )

    html = render_html(status_path, out_path, status)

    assert_decision_badge(html, label="STAGE-PASS", badge_class="badge-pass")
    assert "External detectors" in html
    assert "Detector rows" in html
    assert "external.all_pass" in html
    assert "external.summaries_present" in html
    assert "external.summary_count" in html
    assert "promptfoo" in html
    assert "llamaguard" in html
    assert "0.910" in html
    assert "0.950" in html


def test_refusal_delta_section_renders_when_refusal_metrics_present(
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"

    status = base_status()
    status["gates"]["refusal_delta_pass"] = False
    status["metrics"].update(
        {
            "refusal_delta_n": 120,
            "refusal_delta": 0.013,
            "refusal_delta_ci_low": -0.005,
            "refusal_delta_ci_high": 0.031,
            "refusal_policy": "mcnemar_two_sided",
            "refusal_p_mcnemar": 0.42,
            "refusal_pass_min": True,
            "refusal_pass_strict": False,
        }
    )

    assert decision_from_status(status, status_path=status_path) == (
        "STAGE-PASS",
        "badge-pass",
    )

    html = render_html(status_path, out_path, status)

    assert_decision_badge(html, label="STAGE-PASS", badge_class="badge-pass")
    assert "Stability / refusal-delta" in html
    assert "metrics.refusal_delta_n" in html
    assert "metrics.refusal_delta" in html
    assert "metrics.refusal_policy" in html
    assert "gates.refusal_delta_pass" in html
    assert "mcnemar_two_sided" in html
    assert "0.013" in html
    assert "0.420" in html


def test_epf_hazard_overlay_renders_with_diagnostic_copy(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"

    status = base_status()
    status["gates"]["epf_hazard_ok"] = False
    status["metrics"].update(
        {
            "hazard_zone": "amber",
            "hazard_E": 0.40,
            "hazard_T": 0.62,
            "hazard_S": 0.58,
            "hazard_D": 0.11,
            "hazard_reason": "epf shadow threshold exceeded",
            "hazard_topology_region": "ridge",
            "hazard_baseline_ok": True,
            "hazard_gate_id": "epf_hazard_ok",
            "hazard_T_scaled": 0.620,
            "hazard_stability_map_schema": "stability_map_v0",
            "hazard_stability_map_path": "artifacts/stability_map_v0.json",
        }
    )

    assert decision_from_status(status, status_path=status_path) == (
        "STAGE-PASS",
        "badge-pass",
    )

    html = render_html(status_path, out_path, status)

    assert_decision_badge(html, label="STAGE-PASS", badge_class="badge-pass")
    assert "EPF hazard overlay" in html
    assert (
        "Diagnostic overlay only. status.json and gate enforcement remain the source of truth."
        in html
    )
    assert "metrics.hazard_zone" in html
    assert "metrics.hazard_reason" in html
    assert "metrics.hazard_topology_region" in html
    assert "metrics.hazard_stability_map_path" in html
    assert "amber" in html
    assert "ridge" in html
    assert "artifacts/stability_map_v0.json" in html


def test_optional_diagnostic_sections_are_absent_when_inputs_are_missing(
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"

    status = base_status()

    assert decision_from_status(status, status_path=status_path) == (
        "STAGE-PASS",
        "badge-pass",
    )

    html = render_html(status_path, out_path, status)

    assert_decision_badge(html, label="STAGE-PASS", badge_class="badge-pass")
    assert "External detectors" not in html
    assert "Stability / refusal-delta" not in html
    assert "EPF hazard overlay" not in html
