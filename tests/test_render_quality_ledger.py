import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.render_quality_ledger import write_quality_ledger  # noqa: E402


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_policy(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "policy:",
                "  id: pulse-gate-policy-v0",
                '  version: "0.1.1"',
                "gates:",
                "  required:",
                "    - pass_controls_refusal",
                "    - pass_controls_sanit",
                "    - sanitization_effective",
                "    - q1_grounded_ok",
                "    - q4_slo_ok",
                "  core_required:",
                "    - pass_controls_refusal",
                "    - pass_controls_sanit",
                "    - sanitization_effective",
                "    - q1_grounded_ok",
                "    - q4_slo_ok",
                "  advisory: []",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_write_quality_ledger_renders_from_status_path(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    write_policy(policy_path)

    write_json(
        status_path,
        {
            "version": "1.0.0-core",
            "created_utc": "2026-02-17T12:34:56Z",
            "metrics": {
                "run_mode": "core",
                "RDSI": 0.93,
                "gate_policy_path": str(policy_path),
            },
            "gates": {
                "pass_controls_refusal": True,
                "pass_controls_sanit": True,
                "sanitization_effective": True,
                "q1_grounded_ok": True,
                "q4_slo_ok": True,
            },
        },
    )

    rendered = write_quality_ledger(status_path, out_path)

    assert rendered == out_path.resolve()
    html = read_text(out_path)
    assert "PULSE Quality Ledger" in html
    assert "STAGE-PASS" in html
    assert "q1_grounded_ok" in html
    assert "q4_slo_ok" in html


def test_write_quality_ledger_is_read_only_over_status_json(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"

    original = {
        "version": "1.0.0-demo",
        "created_utc": "2026-02-17T12:34:56Z",
        "metrics": {"run_mode": "demo"},
        "gates": {"q1_grounded_ok": True},
    }
    write_json(status_path, original)
    before = status_path.read_bytes()

    write_quality_ledger(status_path, out_path)

    after = status_path.read_bytes()
    assert after == before
    assert json.loads(after.decode("utf-8")) == original


def test_write_quality_ledger_tolerates_missing_optional_sections(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"

    write_json(
        status_path,
        {
            "version": "1.0.0-demo",
            "created_utc": "2026-02-17T12:34:56Z",
            "metrics": {"run_mode": "demo"},
            "gates": {},
        },
    )

    write_quality_ledger(status_path, out_path)

    html = read_text(out_path)
    assert "PULSE Quality Ledger" in html
    assert "UNKNOWN" in html


def test_advisory_gate_does_not_flip_decision_banner(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    write_policy(policy_path)

    write_json(
        status_path,
        {
            "version": "1.0.0-core",
            "created_utc": "2026-02-17T12:34:56Z",
            "metrics": {
                "run_mode": "core",
                "gate_policy_path": str(policy_path),
            },
            "gates": {
                "pass_controls_refusal": True,
                "pass_controls_sanit": True,
                "sanitization_effective": True,
                "q1_grounded_ok": True,
                "q4_slo_ok": True,
                "external_summaries_present": False,
            },
        },
    )

    write_quality_ledger(status_path, out_path)

    html = read_text(out_path)
    assert "STAGE-PASS" in html
    assert "external_summaries_present" in html


def test_run_all_still_writes_report_card_via_renderer(tmp_path: Path) -> None:
    script = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "run_all.py"
    artifact_dir = tmp_path / "artifacts"

    env = dict(os.environ)
    env["PULSE_ARTIFACT_DIR"] = str(artifact_dir)
    env["PULSE_RUN_MODE"] = "demo"

    result = subprocess.run(
        [sys.executable, str(script), "--mode", "demo"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert (artifact_dir / "status.json").exists()
    assert (artifact_dir / "report_card.html").exists()

    html = read_text(artifact_dir / "report_card.html")
    assert "PULSE Quality Ledger" in html
    assert "DEMO-PASS" in html
    assert "UNKNOWN" not in html
