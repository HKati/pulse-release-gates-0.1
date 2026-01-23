from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, (
        f"Command failed:\n{' '.join(cmd)}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    )


def test_paradox_core_summary_is_deterministic(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    py = sys.executable  # virtualenv/pyenv safe

    field = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "field_v0.json"
    edges = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "edges_v0.jsonl"

    core = tmp_path / "core.json"
    md1 = tmp_path / "core_summary_1.md"
    md2 = tmp_path / "core_summary_2.md"

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

    # Render summary twice from the same core input; output must be byte-identical.
    _run(
        [
            py,
            str(repo_root / "scripts" / "inspect_paradox_core_v0.py"),
            "--in",
            str(core),
            "--out",
            str(md1),
        ]
    )
    _run(
        [
            py,
            str(repo_root / "scripts" / "inspect_paradox_core_v0.py"),
            "--in",
            str(core),
            "--out",
            str(md2),
        ]
    )

    b1 = md1.read_bytes()
    b2 = md2.read_bytes()
    assert b1 == b2, "Core summary markdown must be byte-identical across reruns"

    text = md1.read_text(encoding="utf-8")

    # Non-causal + CI-neutral assertions (reviewer contract).
    assert "non-causal" in text
    assert "CI" in text and "neutral" in text

    # Tie-break visibility: with equal severity, atom_id lex asc should win.
    # We check order in the output by index.
    i1 = text.find("`a_01`")
    i2 = text.find("`a_02`")
    assert i1 != -1 and i2 != -1 and i1 < i2, "Expected a_01 before a_02 in the summary"
