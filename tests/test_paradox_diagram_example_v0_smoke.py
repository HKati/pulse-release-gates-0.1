from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_paradox_diagram_example_v0_smoke(tmp_path: Path) -> None:
    root = _repo_root()

    example = root / "schemas" / "examples" / "paradox_diagram_input_v0.example.json"
    contract = root / "scripts" / "check_paradox_diagram_input_v0_contract.py"
    renderer = root / "tools" / "render_paradox_diagram_v0.py"

    assert example.exists(), "example input is missing"
    assert contract.exists(), "contract checker script is missing"
    assert renderer.exists(), "renderer script is missing"

    out = tmp_path / "paradox_diagram_example_v0.svg"

    subprocess.check_call([sys.executable, str(contract), "--in", str(example)], cwd=str(root))
    subprocess.check_call([sys.executable, str(renderer), "--in", str(example), "--out", str(out)], cwd=str(root))

    assert out.exists(), "renderer did not produce SVG"

    txt = out.read_text(encoding="utf-8")
    assert "<svg" in txt, "output does not look like SVG"
    # Keep the assertion stable but not too brittle
    assert "PULSE - Paradox diagram" in txt, "expected renderer title string not found"
