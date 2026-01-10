#!/usr/bin/env python3
"""
paradox_core_reviewer_bundle_v0.py

Deterministic reviewer bundle builder for Paradox Core v0 (+ Paradox Diagram v0).

Inputs:
  - paradox_field_v0.json
  - (optional) paradox_edges_v0.jsonl

Outputs (in --out-dir):
  - paradox_core_v0.json
  - paradox_core_summary_v0.md
  - paradox_core_v0.svg
  - paradox_diagram_v0.json
  - paradox_diagram_v0.svg
  - paradox_core_reviewer_card_v0.html

Design goals:
  - CI-neutral (diagnostic overlay)
  - pinned by construction: delegates to already deterministic scripts
  - no timestamps, no env-dependent absolute paths in HTML
  - produces a single offline-openable reviewer card
  - semantics live in artifacts; render is render-only
"""

from __future__ import annotations

import argparse
import html
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def _run(cmd: List[str], cwd: Optional[Path] = None) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd) if cwd else None)
    if r.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(cmd)
            + "\n\nSTDOUT:\n"
            + r.stdout
            + "\n\nSTDERR:\n"
            + r.stderr
        )


def _as_repo_path(p: Path, repo_root: Path) -> Path:
    """
    Interpret relative paths as repo-root-relative (stable for CI and reproducibility).
    Absolute paths are left unchanged.
    """
    if p.is_absolute():
        return p
    return repo_root / p


def _to_repo_rel_str(p: Path, repo_root: Path) -> str:
    """
    Prefer repo-relative strings for subprocess args (keeps path_hint stable),
    but fall back to absolute if outside repo.
    """
    try:
        return str(p.resolve().relative_to(repo_root.resolve()))
    except Exception:
        return str(p.resolve())


def _write_reviewer_card_html(out_dir: Path, title: str) -> Path:
    core_json = out_dir / "paradox_core_v0.json"
    summary_md = out_dir / "paradox_core_summary_v0.md"
    core_svg = out_dir / "paradox_core_v0.svg"

    diagram_json = out_dir / "paradox_diagram_v0.json"
    diagram_svg = out_dir / "paradox_diagram_v0.svg"

    out_html = out_dir / "paradox_core_reviewer_card_v0.html"

    # Read summary as plain text and render in <pre> (no markdown rendering dependency).
    summary_text = ""
    if summary_md.exists():
        summary_text = summary_md.read_text(encoding="utf-8")

    # Diagram block (IMPORTANT: precompute to avoid f-string expression backslash issues)
    if diagram_svg.exists():
        diagram_block_html = f'<img src="{diagram_svg.name}" alt="Paradox Diagram v0 SVG"/>'
    else:
        diagram_block_html = "<em>(diagram SVG not present)</em>"

    # Build artifact links (relative filenames only; stable).
    artifact_links: List[str] = []
    if core_json.exists():
        artifact_links.append(f'<a href="{core_json.name}">{core_json.name}</a>')
    if summary_md.exists():
        artifact_links.append(f'<a href="{summary_md.name}">{summary_md.name}</a>')
    if core_svg.exists():
        artifact_links.append(f'<a href="{core_svg.name}">{core_svg.name}</a>')
    if diagram_json.exists():
        artifact_links.append(f'<a href="{diagram_json.name}">{diagram_json.name}</a>')
    if diagram_svg.exists():
        artifact_links.append(f'<a href="{diagram_svg.name}">{diagram_svg.name}</a>')

    artifacts_html = "\n    ".join(artifact_links) if artifact_links else "<em>(no artifacts found)</em>"

    # Stable, dependency-free HTML (no timestamps; only relative links).
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
      line-height: 1.35;
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
    <div><strong>Diagnostic projection only.</strong> CI-neutral by default unless explicitly promoted.</div>
    <div>Non-causal guardrails: <code>co_occurrence</code> edges are undirected (association only).</div>
    <div>Arrows are reference-only: <code>atom → reference</code> anchors (not atom → atom causality).</div>
  </div>

  <div class="card links">
    <strong>Artifacts</strong><br/>
    {artifacts_html}
  </div>

  <div class="grid">
    <div class="card">
      <strong>Paradox Core v0 — SVG (deterministic render)</strong><br/><br/>
      <img src="{core_svg.name}" alt="Paradox Core v0 SVG"/>
    </div>

    <div class="card">
      <strong>Paradox Diagram v0 — SVG (deterministic render)</strong><br/><br/>
      {diagram_block_html}
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

    # Normalize inputs as repo-root-relative by default (deterministic CI behavior)
    field_path = _as_repo_path(Path(args.field), repo_root)
    edges_path = _as_repo_path(Path(args.edges), repo_root) if args.edges else None
    out_dir = _as_repo_path(Path(args.out_dir), repo_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    core_json = out_dir / "paradox_core_v0.json"
    summary_md = out_dir / "paradox_core_summary_v0.md"
    core_svg = out_dir / "paradox_core_v0.svg"

    diagram_json = out_dir / "paradox_diagram_v0.json"
    diagram_svg = out_dir / "paradox_diagram_v0.svg"

    # Helper strings for subprocess args (prefer repo-relative)
    field_arg = _to_repo_rel_str(field_path, repo_root)
    core_json_arg = _to_repo_rel_str(core_json, repo_root)
    summary_md_arg = _to_repo_rel_str(summary_md, repo_root)
    core_svg_arg = _to_repo_rel_str(core_svg, repo_root)

    diagram_json_arg = _to_repo_rel_str(diagram_json, repo_root)
    diagram_svg_arg = _to_repo_rel_str(diagram_svg, repo_root)

    edges_arg = _to_repo_rel_str(edges_path, repo_root) if edges_path else None

    # 1) Build core JSON
    cmd_core = [
        py,
        str(scripts_dir / "paradox_core_projection_v0.py"),
        "--field",
        field_arg,
        "--out",
        core_json_arg,
        "--k",
        str(int(args.k)),
        "--metric",
        str(args.metric),
    ]
    if edges_arg:
        cmd_core += ["--edges", edges_arg]
    _run(cmd_core, cwd=repo_root)

    # 2) Contract check (fail-closed, overlay-local)
    _run(
        [
            py,
            str(scripts_dir / "check_paradox_core_v0_contract.py"),
            "--in",
            core_json_arg,
        ],
        cwd=repo_root,
    )

    # 3) Markdown summary
    _run(
        [
            py,
            str(scripts_dir / "inspect_paradox_core_v0.py"),
            "--in",
            core_json_arg,
            "--out",
            summary_md_arg,
        ],
        cwd=repo_root,
    )

    # 4) Deterministic SVG render (core)
    _run(
        [
            py,
            str(scripts_dir / "render_paradox_core_svg_v0.py"),
            "--in",
            core_json_arg,
            "--out",
            core_svg_arg,
            "--width",
            str(int(args.svg_width)),
            "--node-w",
            str(int(args.node_w)),
            "--node-h",
            str(int(args.node_h)),
            "--max-summary-len",
            str(int(args.max_summary_len)),
        ],
        cwd=repo_root,
    )

    # 5) Build Paradox Diagram v0 (derived strictly from Core artifact)
    cmd_diagram = [
        py,
        str(scripts_dir / "paradox_diagram_from_core_v0.py"),
        "--core",
        core_json_arg,
        "--out",
        diagram_json_arg,
    ]
    if edges_arg:
        # Optional in v0; recorded as input sha256 only
        cmd_diagram += ["--edges", edges_arg]
    _run(cmd_diagram, cwd=repo_root)

    # 6) Diagram contract check (fail-closed)
    _run(
        [
            py,
            str(scripts_dir / "check_paradox_diagram_v0_contract.py"),
            "--in",
            diagram_json_arg,
        ],
        cwd=repo_root,
    )

    # 7) Deterministic SVG render (diagram)
    _run(
        [
            py,
            str(scripts_dir / "render_paradox_diagram_svg_v0.py"),
            "--in",
            diagram_json_arg,
            "--out",
            diagram_svg_arg,
        ],
        cwd=repo_root,
    )

    # 8) Reviewer card HTML (static, no external deps)
    _write_reviewer_card_html(out_dir=out_dir, title="Paradox Core Reviewer Card v0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
