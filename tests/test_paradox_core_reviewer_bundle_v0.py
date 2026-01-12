from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Dict


def _run(cmd: list[str], cwd: Path) -> None:
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(
            "Command failed:\n"
            + " ".join(cmd)
            + "\n\nSTDOUT:\n"
            + (r.stdout or "")
            + "\n\nSTDERR:\n"
            + (r.stderr or "")
        )


def _snapshot(out_dir: Path, files: list[str]) -> Dict[str, bytes]:
    snap: Dict[str, bytes] = {}
    for name in files:
        p = out_dir / name
        if not p.exists():
            raise AssertionError(f"Expected output missing: {p}")
        b = p.read_bytes()
        if len(b) == 0:
            raise AssertionError(f"Expected output is empty: {p}")
        snap[name] = b
    return snap


def test_reviewer_bundle_emits_diagram_and_is_idempotent(tmp_path: Path) -> None:
    """
    Integration test:
      - run reviewer bundle builder on fixture inputs
      - require diagram JSON (meaning layer)
      - allow diagram SVG best-effort, but if present it must be non-empty
      - re-run into the same out-dir and assert byte-stable outputs (determinism)
    """
    repo_root = Path(__file__).resolve().parents[1]

    script = repo_root / "scripts" / "paradox_core_reviewer_bundle_v0.py"
    assert script.exists(), f"Missing script: {script}"

    field = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "field_v0.json"
    edges = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "edges_v0.jsonl"
    assert field.exists(), f"Missing fixture: {field}"
    assert edges.exists(), f"Missing fixture: {edges}"

    out_dir = tmp_path / "paradox_core_bundle_v0"

    cmd = [
        sys.executable,
        str(script),
        "--field",
        str(field),
        "--edges",
        str(edges),
        "--out-dir",
        str(out_dir),
        "--k",
        "2",
        "--metric",
        "severity",
    ]

    # First run
    _run(cmd, cwd=repo_root)

    # Required bundle outputs (diagram JSON is required)
    required = [
        "paradox_core_v0.json",
        "paradox_core_summary_v0.md",
        "paradox_core_v0.svg",
        "paradox_core_reviewer_card_v0.html",
        "paradox_diagram_v0.json",
    ]
    snap1 = _snapshot(out_dir, required)

    # Diagram SVG: best-effort optional, but if present must be non-empty
    svg = out_dir / "paradox_diagram_v0.svg"
    if svg.exists():
        if svg.stat().st_size == 0:
            raise AssertionError("paradox_diagram_v0.svg is present but empty")

    # Re-run into the same out-dir → outputs must be byte-stable (idempotent/deterministic)
    _run(cmd, cwd=repo_root)

    snap2 = _snapshot(out_dir, required)

    for name in required:
        if snap1[name] != snap2[name]:
            raise AssertionError(f"Output drift detected across rerun: {name}")

    # Reviewer card should link diagram artifacts when present (stable relative references)
    html_text = (out_dir / "paradox_core_reviewer_card_v0.html").read_text(encoding="utf-8", errors="replace")
    if "paradox_diagram_v0.json" not in html_text:
        raise AssertionError("Reviewer card HTML does not reference paradox_diagram_v0.json")
    # SVG link may be missing if SVG isn't produced; don't require it.
