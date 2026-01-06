from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, (
        f"Command failed:\n{' '.join(cmd)}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    )


def test_paradox_core_svg_is_deterministic(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    py = sys.executable  # virtualenv/pyenv safe

    field = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "field_v0.json"
    edges = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "edges_v0.jsonl"

    core = tmp_path / "core.json"
    svg1 = tmp_path / "core_1.svg"
    svg2 = tmp_path / "core_2.svg"

    # Build a core artifact (k=2 keeps the tie-break case: a_01 before a_02).
    _run(
        [
            py,
            str(repo_root / "scripts" / "paradox_core_projection_v0.py"),
            "--field",
            str(field),
            "--edges",
            str(edges),
            "--out",
            str(core),
            "--k",
            "2",
            "--metric",
            "severity",
        ]
    )

    # Render SVG twice from the same core input; output must be byte-identical.
    _run(
        [
            py,
            str(repo_root / "scripts" / "render_paradox_core_svg_v0.py"),
            "--in",
            str(core),
            "--out",
            str(svg1),
        ]
    )
    _run(
        [
            py,
            str(repo_root / "scripts" / "render_paradox_core_svg_v0.py"),
            "--in",
            str(core),
            "--out",
            str(svg2),
        ]
    )

    b1 = svg1.read_bytes()
    b2 = svg2.read_bytes()
    assert b1 == b2, "Core SVG output must be byte-identical across reruns"

    text = svg1.read_text(encoding="utf-8")

    # Reviewer contract: explicit non-causal + CI-neutral wording must be present.
    assert "non-causal" in text
    assert "CI-neutral" in text

    # Tie-break visibility: with equal severity, atom_id lex asc should win.
    # In the SVG, nodes are emitted in core_rank order; check ordering in output.
    i1 = text.find('id="atom-a_01"')
    i2 = text.find('id="atom-a_02"')
    assert i1 != -1 and i2 != -1 and i1 < i2, "Expected a_01 before a_02 in the SVG"
