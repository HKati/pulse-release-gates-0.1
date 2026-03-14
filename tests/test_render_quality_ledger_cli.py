import json
import subprocess
import sys
from pathlib import Path


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_render_quality_ledger_cli_smoke_status_out(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    out_path = tmp_path / "report_card.html"

    write_json(
        status_path,
        {
            "version": "1.0.0-core",
            "created_utc": "2026-02-17T12:34:56Z",
            "metrics": {
                "run_mode": "core",
                "required_gates": [
                    "pass_controls_refusal",
                    "pass_controls_sanit",
                    "sanitization_effective",
                    "q1_grounded_ok",
                    "q4_slo_ok",
                ],
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

    script = Path("PULSE_safe_pack_v0/tools/render_quality_ledger.py").resolve()

    result = subprocess.run(
        [sys.executable, str(script), "--status", str(status_path), "--out", str(out_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert out_path.exists()

    html = out_path.read_text(encoding="utf-8")
    assert "PULSE Quality Ledger" in html
    assert "STAGE-PASS" in html
    assert "Rendered" in result.stdout
