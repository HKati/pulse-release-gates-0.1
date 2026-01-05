from __future__ import annotations

import subprocess
from pathlib import Path


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"Command failed:\n{' '.join(cmd)}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"


def test_paradox_core_projection_is_deterministic(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    field = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "field_v0.json"
    edges = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "edges_v0.jsonl"

    out1 = tmp_path / "core1.json"
    out2 = tmp_path / "core2.json"

    _run(["python", str(repo_root / "scripts" / "paradox_core_projection_v0.py"),
          "--field", str(field),
          "--edges", str(edges),
          "--out", str(out1),
          "--k", "2",
          "--metric", "severity"])

    _run(["python", str(repo_root / "scripts" / "paradox_core_projection_v0.py"),
          "--field", str(field),
          "--edges", str(edges),
          "--out", str(out2),
          "--k", "2",
          "--metric", "severity"])

    b1 = out1.read_bytes()
    b2 = out2.read_bytes()
    assert b1 == b2, "Core projection output must be byte-identical across reruns"

    _run(["python", str(repo_root / "scripts" / "check_paradox_core_v0_contract.py"),
          "--in", str(out1)])
