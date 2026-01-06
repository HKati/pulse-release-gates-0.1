from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, (
        f"Command failed:\n{' '.join(cmd)}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    )


def test_paradox_core_svg_matches_golden_k2(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    py = sys.executable  # virtualenv/pyenv safe

    field = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "field_v0.json"
    edges = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "edges_v0.jsonl"

    golden = repo_root / "tests" / "fixtures" / "paradox_core_render_v0" / "golden_core_k2.svg"

    core = tmp_path / "core_k2.json"
    svg = tmp_path / "core_k2.svg"

    # Build core (k=2) from the canonical fixtures.
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

    # Render SVG from the core.
    _run(
        [
            py,
            str(repo_root / "scripts" / "render_paradox_core_svg_v0.py"),
            "--in",
            str(core),
            "--out",
            str(svg),
        ]
    )

    got = svg.read_bytes()
    exp = golden.read_bytes()

    assert got == exp, (
        "Rendered SVG does not match golden fixture.\n"
        "If this change is intentional, regenerate and update:\n"
        "  tests/fixtures/paradox_core_render_v0/golden_core_k2.svg\n"
    )
