from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(
            "Command failed:\n"
            + " ".join(cmd)
            + "\n\nSTDOUT:\n"
            + r.stdout
            + "\n\nSTDERR:\n"
            + r.stderr
        )


def test_render_paradox_diagram_svg_v0_is_deterministic(tmp_path: Path) -> None:
    """
    Determinism smoke test:
      - run the renderer twice on the same fixture
      - outputs must be byte-for-byte identical
    """
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "render_paradox_diagram_svg_v0.py"

    # Use the canonical expected diagram fixture as renderer input.
    inp = repo_root / "tests" / "fixtures" / "paradox_diagram_v0" / "expected_paradox_diagram_v0.json"

    assert script.exists(), f"missing script: {script}"
    assert inp.exists(), f"missing fixture input: {inp}"

    out1 = tmp_path / "diagram1.svg"
    out2 = tmp_path / "diagram2.svg"

    _run([sys.executable, str(script), "--in", str(inp), "--out", str(out1)])
    _run([sys.executable, str(script), "--in", str(inp), "--out", str(out2)])

    t1 = out1.read_text(encoding="utf-8")
    t2 = out2.read_text(encoding="utf-8")

    assert t1 == t2, "SVG output must be byte-for-byte deterministic"
    assert "<svg" in t1, "SVG output must contain <svg>"
    assert "Paradox Diagram v0" in t1, "SVG output must include the default title"
