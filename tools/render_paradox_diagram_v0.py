#!/usr/bin/env python3
"""
Render a deterministic Paradox diagram (v0) as an SVG.

Input (default):
  PULSE_safe_pack_v0/artifacts/paradox_diagram_input_v0.json

Output (default):
  PULSE_safe_pack_v0/artifacts/paradox_diagram_v0.svg

Design goals:
- stdlib-only
- deterministic output
- best-effort friendly (caller/workflow may choose to treat failures as warnings)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _die(msg: str) -> None:
    print(f"[paradox:diagram:error] {msg}", file=sys.stderr)
    raise SystemExit(2)


def _svg_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        _die(f"Input not found: {path}")
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        _die(f"Invalid JSON: {path} ({e})")
    if not isinstance(d, dict):
        _die(f"Top-level JSON must be an object, got {type(d).__name__}")
    return d


def _get_metric(d: Dict[str, Any], key: str) -> Optional[float]:
    m = d.get("metrics")
    if isinstance(m, dict) and key in m:
        v = m.get(key)
    else:
        v = d.get(key)

    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    # tolerate numeric strings (best-effort)
    try:
        return float(v)
    except Exception:
        return None


def _fmt_num(v: Optional[float], *, suffix: str = "", decimals: int = 3) -> str:
    if v is None:
        return "n/a"
    if decimals <= 0:
        return f"{int(round(v))}{suffix}"
    return f"{v:.{decimals}f}{suffix}"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render Paradox diagram v0 (SVG)")
    p.add_argument(
        "--in",
        dest="inp",
        default="PULSE_safe_pack_v0/artifacts/paradox_diagram_input_v0.json",
        help="Path to paradox_diagram_input_v0.json",
    )
    p.add_argument(
        "--out",
        dest="out",
        default="PULSE_safe_pack_v0/artifacts/paradox_diagram_v0.svg",
        help="Output SVG path",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    inp = Path(args.inp)
    out = Path(args.out)

    d = _read_json(inp)

    schema_version = str(d.get("schema_version") or "unknown")
    timestamp_utc = str(d.get("timestamp_utc") or "")
    shadow = d.get("shadow")
    decision_key = str(d.get("decision_key") or d.get("decision") or "UNKNOWN")

    settle_p95 = _get_metric(d, "settle_time_p95_ms")
    settle_budget = _get_metric(d, "settle_time_budget_ms")
    downstream_error_rate = _get_metric(d, "downstream_error_rate")
    paradox_density = _get_metric(d, "paradox_density")

    ratio = None
    if settle_p95 is not None and settle_budget not in (None, 0.0):
        ratio = settle_p95 / float(settle_budget)

    missing = d.get("missing_metrics")
    if not isinstance(missing, list):
        missing = []

    # SVG (simple, deterministic)
    width = 960
    height = 300
    x0 = 20
    y = 32
    line_h = 24

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">')
    lines.append("<style>")
    lines.append("text{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;}")
    lines.append(".title{font-size:20px;font-weight:600;}")
    lines.append(".meta{font-size:12px;fill:#444;}")
    lines.append(".row{font-size:14px;}")
    lines.append("</style>")
    lines.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="#fff" stroke="#ddd"/>')

    lines.append(f'<text x="{x0}" y="{y}" class="title">{_svg_escape("PULSE • Paradox diagram (v0)")}</text>')
    y += line_h
    meta = f"schema_version={schema_version}  decision={decision_key}  shadow={shadow}  timestamp_utc={timestamp_utc}"
    lines.append(f'<text x="{x0}" y="{y}" class="meta">{_svg_escape(meta)}</text>')

    y += line_h * 2

    # Rows
    rows = [
        ("settle_time_p95_ms", _fmt_num(settle_p95, suffix=" ms", decimals=1)),
        ("settle_time_budget_ms", _fmt_num(settle_budget, suffix=" ms", decimals=1)),
        ("settle_ratio", _fmt_num(ratio, decimals=3) if ratio is not None else "n/a"),
        ("downstream_error_rate", _fmt_num(downstream_error_rate, decimals=6)),
        ("paradox_density", _fmt_num(paradox_density, decimals=6)),
    ]

    for k, v in rows:
        lines.append(f'<text x="{x0}" y="{y}" class="row">{_svg_escape(k)}: {_svg_escape(str(v))}</text>')
        y += line_h

    if missing:
        y += int(line_h * 0.5)
        lines.append(
            f'<text x="{x0}" y="{y}" class="meta">{_svg_escape("missing_metrics: " + ", ".join(map(str, missing)))}</text>'
        )

    lines.append("</svg>")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[paradox:diagram] wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
