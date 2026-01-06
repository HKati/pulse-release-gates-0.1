#!/usr/bin/env python3
"""
paradox_core_reviewer_bundle_v0.py

Deterministic reviewer bundle builder for Paradox Core v0.

Inputs:
  - paradox_field_v0.json
  - (optional) paradox_edges_v0.jsonl

Outputs (in --out-dir):
  - paradox_core_v0.json
  - paradox_core_summary_v0.md
  - paradox_core_v0.svg
  - paradox_core_reviewer_card_v0.html

Design goals:
  - CI-neutral (diagnostic overlay)
  - pinned by construction: delegates to already deterministic scripts
  - no timestamps, no env-dependent absolute paths in HTML
  - produces a single offline-openable reviewer card
"""

from __future__ import annotations

import argparse
import html
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def _run(cmd: List[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(cmd)
            + "\n\nSTDOUT:\n"
            + r.stdout
            + "\n\nSTDERR:\n"
            + r.stderr
        )


def _write_reviewer_card_html(out_dir: Path, title: str) -> Path:
    core_json = out_dir / "paradox_core_v0.json"
    summary_md = out_dir / "paradox_core_summary_v0.md"
    svg_file = out_dir / "paradox_core_v0.svg"
    out_html = out_dir / "paradox_core_reviewer_card_v0.html"

    # Read summary as plain text and render in <pre> (no markdown rendering dependency).
    summary_text = ""
    if summary_md.exists():
        summary_text = summary_md.read_text(encoding="utf-8")

    # Stable, dependency-free HTML (no timestamps; only relative links).
    # SVG is referenced as a file for simplicity (keeps this HTML stable and small).
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    body {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      margin: 24px;
      color: #111;
      background: #fff;
    }}
    .note {{
      opacity: 0.9;
      margin-top: 6px;
      margin-bottom: 18px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
    }}
    .card {{
      border: 1px solid #111;
      border-radius: 10px;
      padding: 14px;
    }}
    .links a {{
      margin-right: 12px;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
    }}
    img {{
      max-width: 100%;
      height: auto;
      display: block;
    }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <div class="note">
    Diagnostic projection only. Edges are association/co-occurrence only (non-causal) in v0.
    CI-neutral by default unless explicitly promoted.
  </div>

  <div class="card links">
    <strong>Artifacts</strong><br/>
    <a href="{core_json.name}">{core_json.name}</a>
    <a href="{summary_md.name}">{summary_md.name}</a>
    <a href="{svg_file.name}">{svg_file.name}</a>
  </div>

  <div class="grid">
    <div class="card">
      <strong>SVG (deterministic render)</strong><br/><br/>
      <img src="{svg_file.name}" alt="Paradox Core v0 SVG"/>
    </div>

    <div class="card">
      <strong>Markdown summary (deterministic)</strong><br/><br/>
      <pre>{html.escape(summary_text)}</pre>
    </div>
  </div>
</body>
</html>
"""
    out_html.write_text(page, encoding="utf-8")
    return out_html


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", required=True, help="Path to paradox_field_v0.json")
    ap.add_argument("--edges", required=False, help="Path to paradox_edges_v0.jsonl (optional)")
    ap.add_argument(
        "--out-dir",
        default="out/paradox_core_bundle_v0",
        help="Output directory (default: out/paradox_core_bundle_v0)",
    )
    ap.add_argument("--k", type=int, default=12, help="Core size top-k atoms (default: 12)")
    ap.add_argument("--metric", default="severity", help="Ranking metric (default: severity)")
    ap.add_argument("--svg-width", type=int, default=1200, help="SVG width (default: 1200)")
    ap.add_argument("--node-w", type=int, default=520, help="SVG node width (default: 520)")
    ap.add_argument("--node-h", type=int, default=64, help="SVG node height (default: 64)")
    ap.add_argument(
        "--max-summary-len",
        type=int,
        default=90,
        help="SVG summary truncation length (default: 90)",
    )
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    scripts_dir = repo_root / "scripts"

    py = sys.executable
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    core_json = out_dir / "paradox_core_v0.json"
    summary_md = out_dir / "paradox_core_summary_v0.md"
    svg_file = out_dir / "paradox_core_v0.svg"

    # 1) Build core JSON
    cmd_core = [
        py,
        str(scripts_dir / "paradox_core_projection_v0.py"),
        "--field",
        str(Path(args.field)),
        "--out",
        str(core_json),
        "--k",
        str(int(args.k)),
        "--metric",
        str(args.metric),
    ]
    if args.edges:
        cmd_core += ["--edges", str(Path(args.edges))]
    _run(cmd_core)

    # 2) Contract check (fail-closed, overlay-local)
    _run(
        [
            py,
            str(scripts_dir / "check_paradox_core_v0_contract.py"),
            "--in",
            str(core_json),
        ]
    )

    # 3) Markdown summary
    _run(
        [
            py,
            str(scripts_dir / "inspect_paradox_core_v0.py"),
            "--in",
            str(core_json),
            "--out",
            str(summary_md),
        ]
    )

    # 4) Deterministic SVG render
    _run(
        [
            py,
            str(scripts_dir / "render_paradox_core_svg_v0.py"),
            "--in",
            str(core_json),
            "--out",
            str(svg_file),
            "--width",
            str(int(args.svg_width)),
            "--node-w",
            str(int(args.node_w)),
            "--node-h",
            str(int(args.node_h)),
            "--max-summary-len",
            str(int(args.max_summary_len)),
        ]
    )

    # 5) Reviewer card HTML (static, no external deps)
    _write_reviewer_card_html(out_dir=out_dir, title="Paradox Core Reviewer Card v0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
