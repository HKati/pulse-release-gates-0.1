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


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_top_level_policy(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                'id: pulse-gate-policy-v0',
                'version: "0.1.1"',
                'gates:',
                '  required:',
                '    - prod_gate_ok',
                '  core_required:',
                '    - core_gate_ok',
                '  custom_shadow:',
                '    - shadow_gate_ok',
                '  advisory: []',
                '',
            ]
        ),
        encoding="utf-8",
    )


def write_nested_policy(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                'id: pulse-gate-policy-v0',
                'version: "0.1.1"',
                'policy:',
                '  gates:',
                '    required:',
                '      - nested_prod_gate_ok',
                '    advisory: []',
                '',
            ]
        ),
        encoding="utf-8",
    )


def status_payload(
    *,
    run_mode: str,
    gates: dict,
    gate_policy_path: Path | None = None,
    required_gates: list[str] | None = None,
    required_gate_set: str | None = None,
) -> dict:
    metrics: dict = {
        "run_mode": run_mode,
        "RDSI": 0.93,
    }
    if gate_policy_path is not None:
        metrics["gate_policy_path"] = str(gate_policy_path)
    if required_gates is not None:
        metrics["required_gates"] = required_gates
    if required_gate_set is not None:
        metrics["required_gate_set"] = required_gate_set

    return {
        "version": f"1.0.0-{run_mode}",
        "created_utc": "2026-02-17T12:34:56Z",
        "metrics": metrics,
        "gates": gates,
    }


def render_html(status_path: Path, out_path: Path) -> str:
    write_quality_ledger(status_path, out_path)
    return read_text(out_path)


def assert_decision_badge(html: str, *, label: str, badge_class: str) -> None:
    expected = f'<div class="badge {badge_class}">{escape(label)}</div>'
    assert html.count('class="badge ') == 1
    assert expected in html


def test_decision_banner_renders_prod_pass_for_prod_mode(tmp_path: Path) -> None:
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"

    write_top_level_policy(policy_path)
    status = status_payload(
        run_mode="prod",
        gate_policy_path=policy_path,
        gates={"prod_gate_ok": True},
    )
    write_json(status_path, status)

    assert decision_from_status(status, status_path=status_path) == (
        "PROD-PASS",
        "badge-pass",
    )

    html = render_html(status_path, out_path)

    assert_decision_badge(html, label="PROD-PASS", badge_class="badge-pass")
    assert "prod_gate_ok" in html


def test_decision_banner_renders_plain_pass_for_nonstandard_mode(tmp_path: Path) -> None:
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"

    write_top_level_policy(policy_path)
    status = status_payload(
        run_mode="shadow",
        gate_policy_path=policy_path,
        required_gate_set="custom_shadow",
        gates={"shadow_gate_ok": True},
    )
    write_json(status_path, status)

    assert decision_from_status(status, status_path=status_path) == (
        "PASS",
        "badge-pass",
    )

    html = render_html(status_path, out_path)

    assert_decision_badge(html, label="PASS", badge_class="badge-pass")
    assert "shadow_gate_ok" in html


def test_decision_banner_renders_fail_when_required_gate_is_false(tmp_path: Path) -> None:
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"

    write_top_level_policy(policy_path)
    status = status_payload(
        run_mode="core",
        gate_policy_path=policy_path,
        gates={"core_gate_ok": False},
    )
    write_json(status_path, status)

    assert decision_from_status(status, status_path=status_path) == (
        "FAIL",
        "badge-fail",
    )

    html = render_html(status_path, out_path)

    assert_decision_badge(html, label="FAIL", badge_class="badge-fail")


def test_metrics_required_gates_override_policy_resolution(tmp_path: Path) -> None:
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"

    write_top_level_policy(policy_path)
    status = status_payload(
        run_mode="core",
        gate_policy_path=policy_path,
        required_gates=["direct_gate_ok"],
        gates={
            "direct_gate_ok": True,
            "core_gate_ok": False,
        },
    )
    write_json(status_path, status)

    assert decision_from_status(status, status_path=status_path) == (
        "STAGE-PASS",
        "badge-pass",
    )

    html = render_html(status_path, out_path)

    assert_decision_badge(html, label="STAGE-PASS", badge_class="badge-pass")
    assert "direct_gate_ok" in html


def test_metrics_required_gate_set_override_selects_named_policy_set(tmp_path: Path) -> None:
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"

    write_top_level_policy(policy_path)
    status = status_payload(
        run_mode="demo",
        gate_policy_path=policy_path,
        required_gate_set="custom_shadow",
        gates={
            "shadow_gate_ok": True,
            "core_gate_ok": False,
        },
    )
    write_json(status_path, status)

    assert decision_from_status(status, status_path=status_path) == (
        "DEMO-PASS",
        "badge-pass",
    )

    html = render_html(status_path, out_path)

    assert_decision_badge(html, label="DEMO-PASS", badge_class="badge-pass")
    assert "shadow_gate_ok" in html


def test_nested_policy_gates_fallback_is_used_when_top_level_gates_missing(
    tmp_path: Path,
) -> None:
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"

    write_nested_policy(policy_path)
    status = status_payload(
        run_mode="prod",
        gate_policy_path=policy_path,
        gates={"nested_prod_gate_ok": True},
    )
    write_json(status_path, status)

    assert decision_from_status(status, status_path=status_path) == (
        "PROD-PASS",
        "badge-pass",
    )

    html = render_html(status_path, out_path)

    assert_decision_badge(html, label="PROD-PASS", badge_class="badge-pass")
    assert "nested_prod_gate_ok" in html
