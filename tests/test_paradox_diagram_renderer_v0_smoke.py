from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_paradox_diagram_renderer_produces_svg(tmp_path: Path) -> None:
    root = _repo_root()
    contract = root / "scripts" / "check_paradox_diagram_input_v0_contract.py"
    renderer = root / "tools" / "render_paradox_diagram_v0.py"

    inp = tmp_path / "paradox_diagram_input_v0.json"
    out = tmp_path / "paradox_diagram_v0.svg"

    inp.write_text(
        json.dumps(
            {
                "version": "v0",
                "timestamp_utc": "2026-02-06T00:00:00+00:00",
                "decision": "NORMAL",
                "decision_raw": "NORMAL",
                "settle_time_p95_ms": 10.0,
                "settle_time_budget_ms": 50.0,
                "downstream_error_rate": 0.02,
                "paradox_density": 0.1,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    subprocess.check_call([sys.executable, str(contract), "--in", str(inp)])
    subprocess.check_call([sys.executable, str(renderer), "--in", str(inp), "--out", str(out)])

    assert out.exists(), "renderer did not produce SVG"
    txt = out.read_text(encoding="utf-8")
    assert "<svg" in txt and "Paradox Diagram v0" in txt
