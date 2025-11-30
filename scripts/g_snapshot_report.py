#!/usr/bin/env python
"""
g_snapshot_report.py

Build a human-readable snapshot report from the available overlays:

- g_field_v0.json
- g_field_stability_v0.json
- g_epf_overlay_v0.json
- gpt_external_detection_v0.json

The script is read-only: it does not change any gates or CI behaviour.
It can print the report to stdout or write it to a file.
"""

import argparse
import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _load_json_candidates(candidates: Sequence[Path]) -> Optional[Dict[str, Any]]:
    for p in candidates:
        if p.is_file():
            with p.open("r", encoding="utf-8") as f:
                return json.load(f)
    return None


def _iso_now() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _summarize_g_field(obj: Dict[str, Any]) -> Dict[str, Any]:
    summary = obj.get("summary") or {}
    points = obj.get("points") or []
    g_values: List[float] = []
    for p in points:
        gv = p.get("g_value")
        if isinstance(gv, (int, float)):
            g_values.append(float(gv))

    out: Dict[str, Any] = {
        "num_points": summary.get("num_points", len(points)),
        "g_mean": summary.get("g_mean"),
        "g_std": summary.get("g_std"),
    }
    if g_values:
        out["g_min"] = min(g_values)
        out["g_max"] = max(g_values)
    else:
        out["g_min"] = None
        out["g_max"] = None
    return out


def _summarize_g_epf(obj: Dict[str, Any]) -> Dict[str, Any]:
    diagnostics = obj.get("diagnostics") or {}
    paradox_gate_ids = diagnostics.get("paradox_gate_ids") or []
    points = diagnostics.get("g_points_on_paradox_gates") or []

    gate_set = {g for g in paradox_gate_ids if isinstance(g, str) and g}
    g_values: List[float] = []
    for p in points:
        gv = p.get("g_value")
        if isinstance(gv, (int, float)):
            g_values.append(float(gv))

    out: Dict[str, Any] = {
        "num_paradox_gates": len(gate_set),
        "num_g_points_on_paradox_gates": len(points),
    }
    if g_values:
        out["g_on_paradox_min"] = min(g_values)
        out["g_on_paradox_max"] = max(g_values)
    else:
        out["g_on_paradox_min"] = None
        out["g_on_paradox_max"] = None
    return out


def _summarize_gpt_external(obj: Dict[str, Any]) -> Dict[str, Any]:
    summary = obj.get("summary") or {}
    vendors = summary.get("vendors") or {}
    models = summary.get("models") or {}

    # Top 3 vendors/models by count
    def top_k(d: Dict[str, Any], k: int = 3) -> List[Tuple[str, int]]:
        items: List[Tuple[str, int]] = []
        for k_, v in d.items():
            if isinstance(v, int):
                items.append((k_, v))
        items.sort(key=lambda x: x[1], reverse=True)
        return items[:k]

    out: Dict[str, Any] = {
        "total_records": summary.get("total_records", 0),
        "num_external_gpt": summary.get("num_external_gpt", 0),
        "num_internal": summary.get("num_internal", 0),
        "num_unknown": summary.get("num_unknown", 0),
        "top_vendors": top_k(vendors),
        "top_models": top_k(models),
    }
    return out


def _summarize_g_stability(obj: Dict[str, Any]) -> Dict[str, Any]:
    # We keep this generic: just forward the summary block if present.
    summary = obj.get("summary") or {}
    return summary


def build_report(root: Path) -> Dict[str, Any]:
    """
    Build a structured report from whatever overlays are available.
    """
    def rp(*parts: str) -> Path:
        return root.joinpath(*parts)

    g_field = _load_json_candidates(
        [
            rp("PULSE_safe_pack_v0", "artifacts", "g_field_v0.json"),
            rp("g_field_v0.json"),
        ]
    )
    g_stab = _load_json_candidates(
        [
            rp("PULSE_safe_pack_v0", "artifacts", "g_field_stability_v0.json"),
            rp("g_field_stability_v0.json"),
        ]
    )
    g_epf = _load_json_candidates(
        [
            rp("PULSE_safe_pack_v0", "artifacts", "g_epf_overlay_v0.json"),
            rp("g_epf_overlay_v0.json"),
        ]
    )
    gpt_ext = _load_json_candidates(
        [
            rp("PULSE_safe_pack_v0", "artifacts", "gpt_external_detection_v0.json"),
            rp("gpt_external_detection_v0.json"),
        ]
    )

    report: Dict[str, Any] = {
        "version": "g_snapshot_report_v0",
        "generated_at": _iso_now(),
        "sources": {
            "g_field_v0": g_field is not None,
            "g_field_stability_v0": g_stab is not None,
            "g_epf_overlay_v0": g_epf is not None,
            "gpt_external_detection_v0": gpt_ext is not None,
        },
        "g_field": _summarize_g_field(g_field) if g_field else None,
        "g_field_stability": _summarize_g_stability(g_stab) if g_stab else None,
        "g_epf": _summarize_g_epf(g_epf) if g_epf else None,
        "gpt_external": _summarize_gpt_external(gpt_ext) if gpt_ext else None,
    }

    return report


def format_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# G snapshot report (v0)")
    lines.append("")
    lines.append(f"Generated at: `{report.get('generated_at')}`")
    lines.append("")

    sources = report.get("sources") or {}
    lines.append("## Sources")
    for key, present in sources.items():
        status = "present" if present else "missing"
        lines.append(f"- **{key}**: {status}")
    lines.append("")

    # G-field
    g_field = report.get("g_field")
    lines.append("## G-field overlay (g_field_v0)")
    if not g_field:
        lines.append("_No G-field overlay found._")
    else:
        lines.append(f"- num_points: {g_field.get('num_points')}")
        lines.append(f"- g_mean: {g_field.get('g_mean')}")
        lines.append(f"- g_std: {g_field.get('g_std')}")
        lines.append(f"- g_min: {g_field.get('g_min')}")
        lines.append(f"- g_max: {g_field.get('g_max')}")
    lines.append("")

    # Stability
    g_stab = report.get("g_field_stability")
    lines.append("## G-field stability overlay (g_field_stability_v0)")
    if not g_stab:
        lines.append("_No stability overlay found._")
    else:
        lines.append("Summary (raw):")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(g_stab, indent=2, ensure_ascii=False))
        lines.append("```")
    lines.append("")

    # G-EPF
    g_epf = report.get("g_epf")
    lines.append("## G-EPF overlay (g_epf_overlay_v0)")
    if not g_epf:
        lines.append("_No G-EPF overlay found._")
    else:
        lines.append(f"- num_paradox_gates: {g_epf.get('num_paradox_gates')}")
        lines.append(
            "- num_g_points_on_paradox_gates: "
            f"{g_epf.get('num_g_points_on_paradox_gates')}"
        )
        lines.append(
            f"- g_on_paradox_min: {g_epf.get('g_on_paradox_min')}"
        )
        lines.append(
            f"- g_on_paradox_max: {g_epf.get('g_on_paradox_max')}"
        )
    lines.append("")

    # GPT external
    gpt_ext = report.get("gpt_external")
    lines.append("## GPT external detection overlay (gpt_external_detection_v0)")
    if not gpt_ext:
        lines.append("_No GPT external detection overlay found._")
    else:
        lines.append(f"- total_records: {gpt_ext.get('total_records')}")
        lines.append(f"- num_external_gpt: {gpt_ext.get('num_external_gpt')}")
        lines.append(f"- num_internal: {gpt_ext.get('num_internal')}")
        lines.append(f"- num_unknown: {gpt_ext.get('num_unknown')}")
        lines.append("")
        lines.append("Top vendors:")
        for v, cnt in gpt_ext.get("top_vendors", []):
            lines.append(f"- {v}: {cnt}")
        lines.append("")
        lines.append("Top models:")
        for m, cnt in gpt_ext.get("top_models", []):
            lines.append(f"- {m}: {cnt}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a G snapshot report from available overlays."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory of the repo (default: current directory).",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (markdown or json). Default: markdown.",
    )
    parser.add_argument(
        "--output",
        help="Optional output file. If omitted, the report is printed to stdout.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = build_report(root)

    if args.format == "json":
        text = json.dumps(report, indent=2, ensure_ascii=False)
    else:
        text = format_markdown(report)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
