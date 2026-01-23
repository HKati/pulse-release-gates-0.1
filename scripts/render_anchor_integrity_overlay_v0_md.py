#!/usr/bin/env python3
"""
render_anchor_integrity_overlay_v0_md.py

Render a human-readable Markdown summary for Anchor Integrity v0.

Input:  anchor_integrity_v0.json (diagnostic overlay JSON)
Output: anchor_integrity_overlay_v0.md (Markdown)

Design goals:
- deterministic output (stable ordering, no wall-clock timestamps)
- CI-neutral by default (if input missing, writes a placeholder MD and exits 0)
- does NOT change any normative gate semantics
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _read_json(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not path.exists():
        return None, f"Input JSON not found: {path}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, f"Failed to parse JSON ({path}): {e}"


def _as_str(x: Any) -> str:
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, (int, float)):
        return str(x)
    if isinstance(x, str):
        return x
    return str(x)


def _fmt_float3(x: Any) -> str:
    if x is None:
        return "null"
    try:
        # Reject bool explicitly (bool is subclass of int)
        if isinstance(x, bool):
            return "null"
        v = float(x)
    except Exception:
        return "null"
    return f"{v:.3f}"


def _ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def _sorted_evidence(evidence: Any) -> List[Dict[str, str]]:
    if not isinstance(evidence, list):
        return []
    out: List[Dict[str, str]] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        msg = item.get("message")
        if isinstance(kind, str) and isinstance(msg, str):
            out.append({"kind": kind, "message": msg})
        elif isinstance(msg, str):
            out.append({"kind": _as_str(kind), "message": msg})
    out.sort(key=lambda x: (x.get("kind", ""), x.get("message", "")))
    return out


def _md_escape_inline(s: str) -> str:
    # Minimal escaping for inline markdown.
    return s.replace("\r", " ").replace("\n", " ").strip()


def _render_md(data: Optional[Dict[str, Any]], err: Optional[str], in_path: Path) -> str:
    if data is None:
        # Placeholder, CI-neutral
        lines = []
        lines.append("# Anchor Integrity Overlay (v0)")
        lines.append("")
        lines.append("> CI-neutral diagnostic layer. This file is a best-effort summary.")
        lines.append("")
        lines.append("## Status")
        lines.append("")
        lines.append(f"- Input: `{in_path.as_posix()}`")
        lines.append(f"- Result: **UNAVAILABLE**")
        lines.append("")
        lines.append("## Details")
        lines.append("")
        lines.append(f"- Error: {_md_escape_inline(err or 'unknown error')}")
        lines.append("")
        return "\n".join(lines) + "\n"

    schema = data.get("schema")
    state = data.get("state") or "UNKNOWN"
    rec = data.get("recommendation") or {}
    if not isinstance(rec, dict):
        rec = {}

    response_mode = rec.get("response_mode") or "SILENCE"
    gate_action = rec.get("gate_action") or "CLOSED"
    rationale = rec.get("rationale") or ""

    meta = data.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}

    run_id = meta.get("run_id")
    commit = meta.get("commit")
    generator = meta.get("generator")
    sde = meta.get("source_date_epoch")

    inputs = data.get("inputs") or {}
    if not isinstance(inputs, dict):
        inputs = {}

    status_path = inputs.get("status_path")
    paradox_source_path = inputs.get("paradox_source_path")
    scanned_paths = inputs.get("scanned_paths")
    if not isinstance(scanned_paths, list):
        scanned_paths = []

    inv = data.get("invariants") or {}
    if not isinstance(inv, dict):
        inv = {}

    anchor_presence = inv.get("anchor_presence")
    anchor_coverage = inv.get("anchor_coverage")
    loop_risk = inv.get("loop_risk")
    contradiction_risk = inv.get("contradiction_risk")
    notes = inv.get("notes")

    evidence = _sorted_evidence(data.get("evidence"))

    lines: List[str] = []
    lines.append("# Anchor Integrity Overlay (v0)")
    lines.append("")
    lines.append("> **Hallucination = Anchor Loss.** This overlay does not assert truth; it reports anchor-signal availability and recommends safe response modes.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Schema: `{_as_str(schema)}`")
    lines.append(f"- State: **{_as_str(state)}**")
    lines.append(f"- Recommendation:")
    lines.append(f"  - Response mode: **{_as_str(response_mode)}**")
    lines.append(f"  - Gate action: **{_as_str(gate_action)}**")
    if rationale:
        lines.append(f"- Rationale: {_md_escape_inline(_as_str(rationale))}")
    else:
        lines.append("- Rationale: (not provided)")
    lines.append("")

    lines.append("## Meta")
    lines.append("")
    lines.append(f"- run_id: `{_as_str(run_id)}`")
    lines.append(f"- commit: `{_as_str(commit)}`")
    lines.append(f"- generator: `{_as_str(generator)}`")
    lines.append(f"- source_date_epoch: `{_as_str(sde)}`")
    lines.append("")

    lines.append("## Invariants")
    lines.append("")
    lines.append(f"- anchor_presence: `{_as_str(anchor_presence)}`")
    lines.append(f"- anchor_coverage: `{_fmt_float3(anchor_coverage)}`")
    lines.append(f"- loop_risk: `{_as_str(loop_risk)}`")
    lines.append(f"- contradiction_risk: `{_as_str(contradiction_risk)}`")
    if notes:
        lines.append(f"- notes: {_md_escape_inline(_as_str(notes))}")
    else:
        lines.append("- notes: (none)")
    lines.append("")

    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- status_path: `{_as_str(status_path)}`")
    lines.append(f"- paradox_source_path: `{_as_str(paradox_source_path)}`")
    if scanned_paths:
        lines.append("- scanned_paths:")
        for p in sorted([str(x) for x in scanned_paths]):
            lines.append(f"  - `{_md_escape_inline(p)}`")
    else:
        lines.append("- scanned_paths: (none)")
    lines.append("")

    lines.append("## Evidence (deterministic order)")
    lines.append("")
    if not evidence:
        lines.append("- (none)")
    else:
        max_items = 60
        for item in evidence[:max_items]:
            k = item.get("kind", "note")
            m = item.get("message", "")
            lines.append(f"- **{_md_escape_inline(k)}**: {_md_escape_inline(m)}")
        if len(evidence) > max_items:
            lines.append(f"- … truncated ({len(evidence) - max_items} more)")
    lines.append("")

    lines.append("## Operational note")
    lines.append("")
    lines.append("- This is a **diagnostic overlay**. It must not modify or reinterpret the main PULSE release-gate semantics.")
    lines.append("- If the overlay state is `UNKNOWN` or `ANCHOR_LOST`, the preferred response mode is `SILENCE` (stop rather than speculate).")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--in",
        dest="in_path",
        default="PULSE_safe_pack_v0/artifacts/anchor_integrity_v0.json",
        help="Input anchor_integrity_v0.json path",
    )
    ap.add_argument(
        "--out",
        dest="out_path",
        default="PULSE_safe_pack_v0/artifacts/anchor_integrity_overlay_v0.md",
        help="Output markdown path",
    )
    args = ap.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)

    data, err = _read_json(in_path)
    md = _render_md(data, err, in_path)

    _ensure_parent(out_path)
    out_path.write_text(md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
