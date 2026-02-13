#!/usr/bin/env python3
"""
Render gravity_record_protocol_v0_1 JSON artifact into a concise Markdown summary.

Goals:
- Deterministic output (stable ordering where possible)
- Robust formatting (null/None -> n/a)
- CI-friendly: used in shadow workflows for reviewer visibility
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_text(path: str, text: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


def _is_finite_number(x: Any) -> bool:
    if isinstance(x, bool):
        return False
    if isinstance(x, (int, float)):
        return math.isfinite(float(x))
    return False


def _fmt(x: Any) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "true" if x else "false"
    if _is_finite_number(x):
        v = float(x)
        return f"{v:.6g}"
    s = str(x).strip()
    return s if s else "n/a"


def _summarize_points(points: Any) -> Dict[str, Any]:
    """
    Summarize a list of point objects with keys {r, value, uncertainty?, n?}.
    Handles mixed r types by computing numeric ranges when possible.
    """
    out: Dict[str, Any] = {
        "count": 0,
        "r_min": None,
        "r_max": None,
        "value_min": None,
        "value_max": None,
        "numeric_r_count": 0,
        "string_r_count": 0,
    }

    if not isinstance(points, list) or len(points) == 0:
        return out

    out["count"] = len(points)

    r_nums: List[float] = []
    v_nums: List[float] = []

    for p in points:
        if not isinstance(p, dict):
            continue
        r = p.get("r")
        v = p.get("value")

        if _is_finite_number(r):
            r_nums.append(float(r))
            out["numeric_r_count"] += 1
        elif isinstance(r, str) and r.strip():
            out["string_r_count"] += 1

        if _is_finite_number(v):
            v_nums.append(float(v))

    if r_nums:
        out["r_min"] = min(r_nums)
        out["r_max"] = max(r_nums)
    if v_nums:
        out["value_min"] = min(v_nums)
        out["value_max"] = max(v_nums)

    return out


def _profile_line(name: str, prof: Any) -> str:
    if not isinstance(prof, dict):
        return f"- **{name}**: `n/a` (missing/invalid profile object)"
    status = _fmt(prof.get("status"))
    pts = prof.get("points")
    s = _summarize_points(pts)

    parts: List[str] = []
    parts.append(f"- **{name}**: status=`{status}`")
    parts.append(f"points={s['count']}")

    if s["value_min"] is not None and s["value_max"] is not None:
        parts.append(f"value_range=[{_fmt(s['value_min'])}, {_fmt(s['value_max'])}]")

    # Only show r range if numeric r exists
    if s["numeric_r_count"] > 0 and s["r_min"] is not None and s["r_max"] is not None:
        parts.append(f"r_range=[{_fmt(s['r_min'])}, {_fmt(s['r_max'])}]")

    return " ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Input gravity_record_protocol_v0_1 JSON")
    ap.add_argument("--out", dest="out_path", required=True, help="Output Markdown path")
    args = ap.parse_args()

    try:
        obj = _read_json(args.in_path)
    except Exception as e:
        # Renderer is diagnostic; but for a baseline module we still prefer a hard failure here.
        raise SystemExit(f"render: cannot read JSON: {type(e).__name__}: {e}")

    schema = obj.get("schema")
    schema_version = obj.get("schema_version")
    source_kind = obj.get("source_kind")
    prov_any = obj.get("provenance")
    prov = prov_any if isinstance(prov_any, dict) else {}

    lines: List[str] = []
    lines.append("# Gravity Record Protocol v0.1 (shadow)")
    lines.append("")
    lines.append("## Artifact")
    lines.append(f"- schema: `{_fmt(schema)}`")
    lines.append(f"- schema_version: `{_fmt(schema_version)}`")
    lines.append(f"- source_kind: `{_fmt(source_kind)}`")
    lines.append(f"- generated_at_utc: `{_fmt(prov.get('generated_at_utc'))}`")
    lines.append(f"- generator: `{_fmt(prov.get('generator'))}`")
    lines.append("")

    cases = obj.get("cases")
    if not isinstance(cases, list) or len(cases) == 0:
        lines.append("## Cases")
        lines.append("- n/a (no cases)")
        lines.append("")
        _write_text(args.out_path, "\n".join(lines) + "\n")
        return 0

    lines.append(f"## Cases ({len(cases)})")
    lines.append("")

    for i, case in enumerate(cases):
        if not isinstance(case, dict):
            lines.append(f"### Case {i+1}")
            lines.append("- n/a (invalid case object)")
            lines.append("")
            continue

        cid = case.get("case_id")
        desc = case.get("description")

        lines.append(f"### Case: `{_fmt(cid)}`")
        if desc is not None:
            lines.append(f"- description: {_fmt(desc)}")
        lines.append("")

        # Stations table
        stations = case.get("stations")
        lines.append("#### Stations")
        if isinstance(stations, list) and stations:
            lines.append("")
            lines.append("| station_id | r_areal | r_label |")
            lines.append("|---|---:|---|")
            for st in stations:
                if not isinstance(st, dict):
                    lines.append("| n/a | n/a | n/a |")
                    continue
                lines.append(
                    f"| `{_fmt(st.get('station_id'))}` | `{_fmt(st.get('r_areal'))}` | `{_fmt(st.get('r_label'))}` |"
                )
            lines.append("")
        else:
            lines.append("- n/a")
            lines.append("")

        # Profiles
        lines.append("#### Profiles")
        profs_any = case.get("profiles")
        profs = profs_any if isinstance(profs_any, dict) else {}
        lines.append(_profile_line("lambda", profs.get("lambda")))
        lines.append(_profile_line("kappa", profs.get("kappa")))
        if "s" in profs:
            lines.append(_profile_line("s", profs.get("s")))
        else:
            lines.append("- **s**: status=`MISSING` (not provided)")
        if "g" in profs:
            lines.append(_profile_line("g", profs.get("g")))
        else:
            lines.append("- **g**: status=`MISSING` (not provided)")
        lines.append("")

        # Derived
        derived = case.get("derived") or {}
        gvl = derived.get("g_vs_lambda") if isinstance(derived, dict) else None
        lines.append("#### Derived")
        if isinstance(gvl, dict):
            lines.append(f"- g_vs_lambda: status=`{_fmt(gvl.get('status'))}` error_norm=`{_fmt(gvl.get('error_norm'))}`")
        else:
            lines.append("- g_vs_lambda: `n/a`")
        lines.append("")

        # Wall classification
        wc = case.get("wall_classification")
        lines.append("#### Wall classification")
        if isinstance(wc, dict):
            lines.append(f"- frequency_wall: `{_fmt(wc.get('frequency_wall'))}`")
            lines.append(f"- delay_wall: `{_fmt(wc.get('delay_wall'))}`")
            lines.append(f"- record_wall: `{_fmt(wc.get('record_wall'))}`")
        else:
            lines.append("- n/a")
        lines.append("")

        lines.append("---")
        lines.append("")

    # raw_errors
    raw_errors = obj.get("raw_errors")
    if isinstance(raw_errors, list) and raw_errors:
        lines.append("## Raw errors")
        for e in raw_errors[:50]:
            lines.append(f"- {_fmt(e)}")
        if len(raw_errors) > 50:
            lines.append(f"- (+{len(raw_errors) - 50} more)")
        lines.append("")

    _write_text(args.out_path, "\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
