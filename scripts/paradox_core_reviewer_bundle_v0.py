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
import hashlib
import html
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------
# subprocess helpers
# -----------------------------
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


# -----------------------------
# Diagram contract check (dep-free fallback)
# -----------------------------
_DIAGRAM_SCHEMA = "PULSE_paradox_diagram_v0"
_DIAGRAM_VERSION = 0


def _has_jsonschema() -> bool:
    try:
        import jsonschema  # noqa: F401
        return True
    except Exception:
        return False


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _id16(prefix: str, payload: str) -> str:
    return f"{prefix}{_sha256_hex(payload)[:16]}"


def _expected_node_id_reference(ref_id: str) -> str:
    return _id16("r_", "ref\n" + ref_id)


def _expected_node_id_atom(core_atom_id: str) -> str:
    return _id16("n_", "atom\n" + core_atom_id)


def _expected_edge_id_co_occurrence(a: str, b: str) -> str:
    aa, bb = sorted([a, b])
    return _id16("e_", "co_occurrence\n" + aa + "\n" + bb)


def _expected_edge_id_reference_relation(atom_node_id: str, ref_node_id: str) -> str:
    return _id16("e_", "reference_relation\n" + atom_node_id + "\n" + ref_node_id)


def _find_diagram_obj(raw: Any) -> Dict[str, Any]:
    """
    Accept either:
      - the diagram artifact itself, or
      - a wrapper object containing a nested diagram artifact.
    Deterministic unwrap: scan nested dicts in sorted key order.
    """
    if not isinstance(raw, dict):
        raise ValueError("Diagram input must be a JSON object.")

    if raw.get("schema") == _DIAGRAM_SCHEMA:
        return raw

    for k in sorted(raw.keys()):
        v = raw.get(k)
        if isinstance(v, dict) and v.get("schema") == _DIAGRAM_SCHEMA:
            return v

    raise ValueError(f"Could not locate diagram object with schema == {_DIAGRAM_SCHEMA}.")


def _basic_check_paradox_diagram_v0(diagram_path: Path) -> None:
    """
    Minimal, dependency-free fail-closed contract check.
    (Used only when jsonschema isn't available in the environment.)

    Enforces the two core invariants + determinism basics:
    - schema/version
    - required notes codes
    - node_id/edge_id uniqueness
    - endpoints exist
    - co_occurrence: undirected, atom-atom, canonical a<=b, stable edge_id
    - reference_relation: atom->reference only, directed true if present, stable edge_id
    - canonical ordering for references/nodes/edges
    - stable node_id recompute
    """
    raw = json.loads(diagram_path.read_text(encoding="utf-8"))
    d = _find_diagram_obj(raw)

    errors: List[str] = []

    def err(msg: str) -> None:
        errors.append(msg)

    # schema/version
    if d.get("schema") != _DIAGRAM_SCHEMA:
        err(f"$.schema must be '{_DIAGRAM_SCHEMA}'")
    if d.get("version") != _DIAGRAM_VERSION:
        err(f"$.version must be {_DIAGRAM_VERSION}")

    # notes required codes
    notes = d.get("notes")
    if not isinstance(notes, list):
        err("$.notes must be a list")
    else:
        codes = []
        for n in notes:
            if isinstance(n, dict) and isinstance(n.get("code"), str):
                codes.append(n["code"])
        for required in ["NON_CAUSAL", "CI_NEUTRAL_DEFAULT"]:
            if required not in codes:
                err(f"$.notes missing required code '{required}'")

    # references ordering
    refs = d.get("references")
    if not isinstance(refs, list) or len(refs) < 1:
        err("$.references must be a non-empty list")
        refs = []
    else:
        ref_ids = []
        for r in refs:
            if not isinstance(r, dict) or not isinstance(r.get("ref_id"), str):
                err("$.references entries must be objects with ref_id")
                continue
            ref_ids.append(r["ref_id"])
        if ref_ids != sorted(ref_ids):
            err("$.references must be sorted by ref_id asc")

    # nodes
    nodes = d.get("nodes")
    if not isinstance(nodes, list) or len(nodes) < 1:
        err("$.nodes must be a non-empty list")
        nodes = []
    node_by_id: Dict[str, Dict[str, Any]] = {}
    for n in nodes:
        if not isinstance(n, dict):
            err("$.nodes contains non-object entry")
            continue
        nid = n.get("node_id")
        if not isinstance(nid, str) or not nid:
            err("$.nodes[].node_id must be a non-empty string")
            continue
        if nid in node_by_id:
            err(f"duplicate node_id: {nid}")
            continue
        node_by_id[nid] = n

    # node_id recompute
    for nid, n in sorted(node_by_id.items(), key=lambda kv: kv[0]):
        kind = n.get("kind")
        if kind == "reference":
            rid = n.get("ref_id")
            if not isinstance(rid, str) or not rid:
                err(f"reference node missing ref_id (node_id={nid})")
            else:
                exp = _expected_node_id_reference(rid)
                if nid != exp:
                    err(f"reference node_id mismatch (node_id={nid}, expected={exp}, ref_id={rid})")
        elif kind == "atom":
            aid = n.get("core_atom_id")
            if not isinstance(aid, str) or not aid:
                err(f"atom node missing core_atom_id (node_id={nid})")
            else:
                exp = _expected_node_id_atom(aid)
                if nid != exp:
                    err(f"atom node_id mismatch (node_id={nid}, expected={exp}, core_atom_id={aid})")
        else:
            err(f"unknown node kind '{kind}' (node_id={nid})")

    # canonical node ordering
    def node_key(n: Dict[str, Any]) -> Tuple[int, str, int, str]:
        if n.get("kind") == "reference":
            return (0, str(n.get("ref_id", "")), 0, "")
        return (1, "", int(n.get("rank", 10**9)), str(n.get("core_atom_id", "")))

    node_keys = [node_key(n) for n in nodes if isinstance(n, dict)]
    if node_keys != sorted(node_keys):
        err("$.nodes must be in canonical order (reference nodes by ref_id, then atoms by rank/core_atom_id)")

    # edges
    edges = d.get("edges")
    if not isinstance(edges, list):
        err("$.edges must be a list")
        edges = []

    edge_ids = set()
    for e in edges:
        if not isinstance(e, dict):
            err("$.edges contains non-object entry")
            continue
        eid = e.get("edge_id")
        if not isinstance(eid, str) or not eid:
            err("$.edges[].edge_id must be a non-empty string")
            continue
        if eid in edge_ids:
            err(f"duplicate edge_id: {eid}")
        edge_ids.add(eid)

    # edge validity + stable ids
    seen_ref_rel = False
    for e in edges:
        if not isinstance(e, dict):
            continue
        kind = e.get("kind")
        a = e.get("a")
        b = e.get("b")
        eid = e.get("edge_id")

        if not isinstance(a, str) or not isinstance(b, str):
            err("edge endpoints a/b must be strings")
            continue

        if a not in node_by_id:
            err(f"edge references missing node a={a}")
            continue
        if b not in node_by_id:
            err(f"edge references missing node b={b}")
            continue

        ak = node_by_id[a].get("kind")
        bk = node_by_id[b].get("kind")

        if kind == "co_occurrence":
            if seen_ref_rel:
                err("co_occurrence edges must precede reference_relation edges")
            if ak != "atom" or bk != "atom":
                err("co_occurrence must connect atom <-> atom")
            if a > b:
                err("co_occurrence endpoints must be canonicalized with a<=b")
            exp = _expected_edge_id_co_occurrence(a, b)
            if isinstance(eid, str) and eid != exp:
                err(f"co_occurrence edge_id mismatch (got={eid}, expected={exp})")
            if "directed" in e:
                err("co_occurrence must not include 'directed'")
        elif kind == "reference_relation":
            seen_ref_rel = True
            if ak != "atom" or bk != "reference":
                err("reference_relation must connect atom -> reference (a atom, b reference)")
            if "directed" in e and e.get("directed") is not True:
                err("reference_relation directed must be true if present")
            exp = _expected_edge_id_reference_relation(a, b)
            if isinstance(eid, str) and eid != exp:
                err(f"reference_relation edge_id mismatch (got={eid}, expected={exp})")
        else:
            err(f"unknown edge kind '{kind}'")

    # canonical edge ordering
    def edge_group(k: str) -> int:
        if k == "co_occurrence":
            return 0
        if k == "reference_relation":
            return 1
        return 9

    def edge_key(e: Dict[str, Any]) -> Tuple[int, str, str, str]:
        return (
            edge_group(str(e.get("kind", ""))),
            str(e.get("a", "")),
            str(e.get("b", "")),
            str(e.get("edge_id", "")),
        )

    edge_keys = [edge_key(e) for e in edges if isinstance(e, dict)]
    if edge_keys != sorted(edge_keys):
        err("$.edges must be in canonical order (co_occurrence then reference_relation; within: a,b,edge_id)")

    if errors:
        msg = "Diagram contract violation(s) (dep-free check):\n" + "\n".join(f" - {x}" for x in errors)
        raise RuntimeError(msg)


# -----------------------------
# Reviewer card HTML
# -----------------------------
def _write_reviewer_card_html(out_dir: Path, title: str) -> Path:
    core_json = out_dir / "paradox_core_v0.json"
    summary_md = out_dir / "paradox_core_summary_v0.md"
    core_svg = out_dir / "paradox_core_v0.svg"

    diagram_json = out_dir / "paradox_diagram_v0.json"
    diagram_svg = out_dir / "paradox_diagram_v0.svg"

    out_html = out_dir / "paradox_core_reviewer_card_v0.html"

    summary_text = ""
    if summary_md.exists():
        summary_text = summary_md.read_text(encoding="utf-8")

    # Precompute HTML snippet (avoid f-string expression escape pitfalls)
    if diagram_svg.exists():
        diagram_block_html = f'<img src="{diagram_svg.name}" alt="Paradox Diagram v0 SVG"/>'
    else:
        diagram_block_html = "<em>(diagram SVG not present)</em>"

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


# -----------------------------
# main
# -----------------------------
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

    # Helper strings for subprocess args (prefer repo-relative) — resolve via cwd=repo_root
    field_arg = _to_repo_rel_str(field_path, repo_root)
    edges_arg = _to_repo_rel_str(edges_path, repo_root) if edges_path else None

    core_json_arg = _to_repo_rel_str(core_json, repo_root)
    summary_md_arg = _to_repo_rel_str(summary_md, repo_root)
    core_svg_arg = _to_repo_rel_str(core_svg, repo_root)

    diagram_json_arg = _to_repo_rel_str(diagram_json, repo_root)
    diagram_svg_arg = _to_repo_rel_str(diagram_svg, repo_root)

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
        cmd_diagram += ["--edges", edges_arg]
    _run(cmd_diagram, cwd=repo_root)

    # 6) Diagram contract check:
    # - If jsonschema exists: run the full contract checker (schema + invariants).
    # - Else: run a dep-free minimal fail-closed check for invariants (keeps bundle workflows dependency-light).
    if _has_jsonschema():
        _run(
            [
                py,
                str(scripts_dir / "check_paradox_diagram_v0_contract.py"),
                "--in",
                diagram_json_arg,
            ],
            cwd=repo_root,
        )
    else:
        # Dep-free, still fail-closed on real contract violations.
        _basic_check_paradox_diagram_v0(diagram_json)

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
