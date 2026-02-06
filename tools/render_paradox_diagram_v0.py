#!/usr/bin/env python3
"""
Render Paradox Diagram v0 (SVG) from paradox_diagram_input_v0.json.

Goals:
- Deterministic, stdlib-only renderer.
- Minimal but useful visualization (text + simple bars).
- Treat missing metrics as explicit N/A (never as 0.0).
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _die(msg: str, code: int = 2) -> "None":
    print(f"[paradox-diagram:render:error] {msg}", file=sys.stderr)
    raise SystemExit(code)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _die(f"Input file not found: {path}")
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON: {path} ({e})")
    if not isinstance(obj, dict):
        _die(f"Top-level JSON must be an object, got {type(obj).__name__}")
    return obj


def _write_text(path: Path, s: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(s, encoding="utf-8")


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def _as_float_or_none(v: Any) -> Optional[float]:
    if v is None:
        return None
    # Reject bool explicitly (bool is an int subclass)
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except Exception:
        return None


def _fmt(v: Optional[float], *, digits: int = 3) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{digits}f}"


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _bar_block(
    *,
    x: int,
    y: int,
    w: int,
    h: int,
    label: str,
    value_text: str,
    ratio01: Optional[float],
) -> str:
    # Outer box
    parts = []
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="white" stroke="black" />')
    parts.append(f'<text x="{x + 12}" y="{y + 22}" font-family="monospace" font-size="14">{_esc(label)}</text>')
    parts.append(
        f'<text x="{x + 12}" y="{y + 42}" font-family="monospace" font-size="12">{_esc(value_text)}</text>'
    )

    # Bar area
    bar_x = x + 12
    bar_y = y + 54
    bar_w = w - 24
    bar_h = 18

    # Background bar (light grey)
    parts.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" fill="#f2f2f2" stroke="black" />')

    if ratio01 is None:
        # N/A overlay hatch-ish (simple diagonal lines)
        for i in range(0, bar_w, 10):
            x1 = bar_x + i
            y1 = bar_y + bar_h
            x2 = bar_x + i + 10
            y2 = bar_y
            parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#999999" stroke-width="1" />')
    else:
        fill_w = int(bar_w * _clamp01(ratio01))
        parts.append(f'<rect x="{bar_x}" y="{bar_y}" width="{fill_w}" height="{bar_h}" fill="#cccccc" stroke="none" />')

    return "\n".join(parts)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render Paradox Diagram v0 SVG (stdlib-only)")
    p.add_argument(
        "--in",
        dest="inp",
        default="PULSE_safe_pack_v0/artifacts/paradox_diagram_input_v0.json",
        help="Input JSON path (paradox_diagram_input_v0.json)",
    )
    p.add_argument(
        "--out",
        dest="out",
        default="PULSE_safe_pack_v0/artifacts/paradox_diagram_v0.svg",
        help="Output SVG path",
    )
    return p.parse_args()


def render_svg(d: Dict[str, Any]) -> str:
    # Header fields (best-effort)
    decision = d.get("decision")
    decision_raw = d.get("decision_raw")
    ts = d.get("timestamp_utc")
    version = d.get("version")

    settle_p95 = _as_float_or_none(d.get("settle_time_p95_ms"))
    settle_budget = _as_float_or_none(d.get("settle_time_budget_ms"))
    derr = _as_float_or_none(d.get("downstream_error_rate"))
    pdens = _as_float_or_none(d.get("paradox_density"))

    # Ratios
    settle_ratio = None
    if settle_p95 is not None and settle_budget is not None and settle_budget > 0:
        # Represent as p95/budget clipped into [0,1] for the bar (>=budget saturates).
        settle_ratio = _clamp01(settle_p95 / settle_budget)

    derr_ratio = None if derr is None else _clamp01(derr)
    pdens_ratio = None if pdens is None else _clamp01(pdens)

    width = 960
    height = 360

    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    lines.append("<desc>")
    lines.append(_esc(json.dumps({"version": version, "timestamp_utc": ts, "decision": decision}, ensure_ascii=False)))
    lines.append("</desc>")

    # Title
    lines.append(f'<text x="24" y="36" font-family="monospace" font-size="20">PULSE • Paradox Diagram v0</text>')
    lines.append(
        f'<text x="24" y="62" font-family="monospace" font-size="12">'
        f'version={_esc(version)}  timestamp_utc={_esc(ts)}'
        f"</text>"
    )
    lines.append(
        f'<text x="24" y="84" font-family="monospace" font-size="12">'
        f'decision={_esc(decision)}  decision_raw={_esc(decision_raw)}'
        f"</text>"
    )

    # Blocks
    lines.append(_bar_block(
        x=24, y=110, w=440, h=100,
        label="settle_time_p95_ms vs budget",
        value_text=f"p95_ms={_fmt(settle_p95)}  budget_ms={_fmt(settle_budget)}  ratio(p95/budget)={_fmt(None if settle_ratio is None else (settle_p95/settle_budget), digits=3)}",
        ratio01=settle_ratio,
    ))

    lines.append(_bar_block(
        x=496, y=110, w=440, h=100,
        label="downstream_error_rate",
        value_text=f"rate={_fmt(derr, digits=4)}  (expected 0..1)",
        ratio01=derr_ratio,
    ))

    lines.append(_bar_block(
        x=24, y=226, w=440, h=100,
        label="paradox_density",
        value_text=f"density={_fmt(pdens, digits=4)}  (expected 0..1)",
        ratio01=pdens_ratio,
    ))

    # Footer note
    lines.append(
        '<text x="24" y="344" font-family="monospace" font-size="11">'
        'Note: N/A means the metric was missing or non-numeric; never coerced to 0.0.'
        "</text>"
    )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = _parse_args()
    inp = Path(args.inp)
    out = Path(args.out)

    d = _read_json(inp)
    svg = render_svg(d)
    _write_text(out, svg)

    print(f"[paradox-diagram:render] wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
