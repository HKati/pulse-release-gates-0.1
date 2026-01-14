#!/usr/bin/env python3
"""
render_separation_phase_overlay_v0_md.py

Deterministic Markdown renderer for separation_phase_v0.json.

Design goals:
- deterministic output (stable ordering; no wall-clock timestamps)
- fail-closed presentation (UNKNOWN/CLOSED when inputs are missing)
- diagnostic only: MUST NOT redefine or influence normative release gating
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _read_json(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _as_str(x: Any) -> Optional[str]:
    if isinstance(x, str) and x.strip():
        return x.strip()
    return None


def _fmt_bool(x: Any) -> str:
    if x is True:
        return "true"
    if x is False:
        return "false"
    if x is None:
        return "null"
    return f"(unexpected: {type(x).__name__})"


def _fmt_score(x: Any) -> str:
    if x is None:
        return "null"
    if isinstance(x, (int, float)):
        return f"{float(x):.3f}"
    return f"(unexpected: {type(x).__name__})"


def _safe_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _truncate(items: List[str], limit: int) -> Tuple[List[str], int]:
    if limit <= 0:
        return [], len(items)
    if len(items) <= limit:
        return items, 0
    return items[:limit], len(items) - limit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--overlay",
        default="PULSE_safe_pack_v0/artifacts/separation_phase_v0.json",
        help="Input separation_phase_v0.json path",
    )
    ap.add_argument(
        "--status",
        default="PULSE_safe_pack_v0/artifacts/status.json",
        help="Optional baseline status.json path (for extra context).",
    )
    ap.add_argument(
        "--out",
        default="PULSE_safe_pack_v0/artifacts/separation_phase_overlay_v0.md",
        help="Output markdown path",
    )
    ap.add_argument(
        "--max-list",
        type=int,
        default=20,
        help="Max items to print per list section (unstable/threshold-like).",
    )
    args = ap.parse_args()

    overlay_path = Path(args.overlay)
    out_path = Path(args.out)

    overlay, overlay_err = _read_json(overlay_path)
    status_path = Path(args.status)
    status = None
    status_err = None
    if status_path.exists():
        status, status_err = _read_json(status_path)

    # Fail-closed presentation if overlay missing/unreadable
    if overlay is None:
        lines: List[str] = []
        lines.append("# Separation Phase Overlay (v0)")
        lines.append("")
        lines.append("**DIAGNOSTIC ONLY.** This report is a read-only rendering of immutable artifacts. It must not redefine release semantics.")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append("- Overlay file: `MISSING/UNREADABLE`")
        lines.append("- State: **UNKNOWN**")
        lines.append("- Recommendation: **CLOSED**")
        lines.append("- Rationale: Overlay JSON could not be read (fail-closed presentation).")
        lines.append("")
        lines.append("## Errors")
        lines.append("")
        lines.append(f"- overlay read error: `{overlay_err}`")
        if status_err:
            lines.append(f"- status read error: `{status_err}`")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 0

    meta = overlay.get("meta") if isinstance(overlay.get("meta"), dict) else {}
    inputs = overlay.get("inputs") if isinstance(overlay.get("inputs"), dict) else {}
    inv = overlay.get("invariants") if isinstance(overlay.get("invariants"), dict) else {}
    rec = overlay.get("recommendation") if isinstance(overlay.get("recommendation"), dict) else {}
    evidence = _safe_list(overlay.get("evidence"))

    state = _as_str(overlay.get("state")) or "UNKNOWN"
    gate_action = _as_str(rec.get("gate_action")) or "CLOSED"
    rationale = _as_str(rec.get("rationale")) or "(no rationale provided)"

    order = inv.get("order_stability") if isinstance(inv.get("order_stability"), dict) else {}
    sep_int = inv.get("separation_integrity") if isinstance(inv.get("separation_integrity"), dict) else {}
    phase_dep = inv.get("phase_dependency") if isinstance(inv.get("phase_dependency"), dict) else {}
    thresh = inv.get("threshold_sensitivity") if isinstance(inv.get("threshold_sensitivity"), dict) else {}

    method = _as_str(order.get("method")) or "unknown"
    score = order.get("score")
    n_runs = order.get("n_runs")
    unstable_gates = sorted([str(x) for x in _safe_list(order.get("unstable_gates"))])

    decision_stable = sep_int.get("decision_stable")
    critical_global_phase = phase_dep.get("critical_global_phase")
    threshold_like_gates = sorted([str(x) for x in _safe_list(thresh.get("threshold_like_gates"))])

    # Baseline decision (optional, best-effort)
    baseline_decision = None
    if isinstance(status, dict):
        for k in ("decision", "release_decision", "level"):
            v = status.get(k)
            if isinstance(v, str) and v.strip():
                baseline_decision = v.strip()
                break

    # Render
    lines2: List[str] = []
    lines2.append("# Separation Phase Overlay (v0)")
    lines2.append("")
    lines2.append("**DIAGNOSTIC ONLY.** This report is a read-only rendering of immutable artifacts. It must not redefine release semantics.")
    lines2.append("")
    lines2.append("## Summary")
    lines2.append("")
    lines2.append(f"- State: **{state}**")
    lines2.append(f"- Recommendation: **{gate_action}**")
    lines2.append(f"- Rationale: {rationale}")
    if baseline_decision:
        lines2.append(f"- Baseline decision (from status.json): `{baseline_decision}`")
    lines2.append("")
    lines2.append("## Inputs")
    lines2.append("")
    lines2.append(f"- overlay: `{overlay_path.as_posix()}`")
    lines2.append(f"- status (optional): `{status_path.as_posix()}`")
    lines2.append(f"- baseline status_path (as recorded): `{_as_str(inputs.get('status_path')) or '(missing)'}`")
    perm_paths = _safe_list(inputs.get("permutation_status_paths"))
    lines2.append(f"- permutation runs: `{len(perm_paths)}`")
    lines2.append("")
    lines2.append("## Invariants")
    lines2.append("")
    lines2.append("### Order stability")
    lines2.append("")
    lines2.append(f"- method: `{method}`")
    lines2.append(f"- score: `{_fmt_score(score)}`")
    lines2.append(f"- n_runs: `{n_runs if isinstance(n_runs, int) else '(unknown)'}`")
    lines2.append(f"- unstable_gates: `{len(unstable_gates)}`")
    lines2.append("")
    lines2.append("### Separation integrity")
    lines2.append("")
    lines2.append(f"- decision_stable: `{_fmt_bool(decision_stable)}`")
    notes = _as_str(sep_int.get("notes"))
    if notes:
        lines2.append(f"- notes: {notes}")
    lines2.append("")
    lines2.append("### Phase dependency")
    lines2.append("")
    lines2.append(f"- critical_global_phase: `{_fmt_bool(critical_global_phase)}`")
    lines2.append("")
    lines2.append("### Threshold sensitivity")
    lines2.append("")
    lines2.append(f"- threshold_like_gates: `{len(threshold_like_gates)}`")
    lines2.append("")

    # Lists (truncated)
    lines2.append("## Unstable gates")
    lines2.append("")
    show_u, more_u = _truncate(unstable_gates, args.max_list)
    if show_u:
        lines2.extend([f"- `{g}`" for g in show_u])
        if more_u:
            lines2.append(f"- … `{more_u}` more")
    else:
        lines2.append("- (none)")
    lines2.append("")

    lines2.append("## Threshold-like gates")
    lines2.append("")
    show_t, more_t = _truncate(threshold_like_gates, args.max_list)
    if show_t:
        lines2.extend([f"- `{g}`" for g in show_t])
        if more_t:
            lines2.append(f"- … `{more_t}` more")
    else:
        lines2.append("- (none)")
    lines2.append("")

    # Evidence (deterministic)
    lines2.append("## Evidence")
    lines2.append("")
    if evidence:
        ev_norm = []
        for e in evidence:
            if isinstance(e, dict):
                kind = _as_str(e.get("kind")) or "note"
                msg = _as_str(e.get("message")) or json.dumps(e, sort_keys=True)
                ev_norm.append((kind, msg))
            else:
                ev_norm.append(("note", str(e)))
        for kind, msg in sorted(ev_norm, key=lambda x: (x[0], x[1])):
            lines2.append(f"- **{kind}**: {msg}")
    else:
        lines2.append("- (none)")
    lines2.append("")

    lines2.append("## Meta")
    lines2.append("")
    lines2.append(f"- commit: `{_as_str(meta.get('commit')) or '(missing)'}`")
    lines2.append(f"- run_id: `{_as_str(meta.get('run_id')) or '(missing)'}`")
    lines2.append(f"- generator: `{_as_str(meta.get('generator')) or '(missing)'}`")
    sde = meta.get("source_date_epoch")
    lines2.append(f"- source_date_epoch: `{sde if isinstance(sde, int) else '(missing)'}`")
    lines2.append("")
    lines2.append("## References")
    lines2.append("")
    lines2.append("- Schema: `schemas/separation_phase_v0.schema.json`")
    lines2.append("- Docs: `docs/SEPARATION_PHASE_v0.md`")
    lines2.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
