#!/usr/bin/env python
"""
Build G snapshot report v0 markdown (shadow-only).

Inputs (if present):

- g_field_v0.json
- g_field_stability_v0.json
- g_epf_overlay_v0.json
- gpt_external_detection_v0.json

The script looks for these overlays either in:
- the repo root, or
- PULSE_safe_pack_v0/artifacts/

and writes:

- PULSE_safe_pack_v0/artifacts/g_snapshot_report_v0.md

This report is CI-neutral: it never changes gates or status.json.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
PACK_ARTIFACTS = REPO_ROOT / "PULSE_safe_pack_v0" / "artifacts"

G_FIELD_NAME = "g_field_v0.json"
G_FIELD_STAB_NAME = "g_field_stability_v0.json"
G_EPF_NAME = "g_epf_overlay_v0.json"
GPT_EXT_NAME = "gpt_external_detection_v0.json"
OUTPUT_NAME = "g_snapshot_report_v0.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _first_existing(*paths: Path) -> Optional[Path]:
    for p in paths:
        if p is not None and p.exists():
            return p
    return None


def _load_json_if_exists(name: str) -> Optional[Dict[str, Any]]:
    path = _first_existing(
        PACK_ARTIFACTS / name,
        REPO_ROOT / name,
    )
    if path is None:
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _truncate_json(data: Any, max_chars: int = 2000) -> str:
    try:
        s = json.dumps(data, indent=2, sort_keys=True)
    except TypeError:
        s = json.dumps(str(data), indent=2)
    if len(s) <= max_chars:
        return s
    # truncate but keep it syntactically readable
    return s[: max_chars - 20] + "\n  ...\n}"


def _checkbox(present: bool) -> str:
    return "x" if present else " "


def summarise_g_field(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not data:
        return {
            "present": False,
            "status": "No G-field overlay found.",
            "traces": None,
            "gates": None,
            "mean": None,
            "min": None,
            "max": None,
            "top_gates": [],
            "raw_snippet": "",
        }
    summary = data.get("summary") or {}
    traces = summary.get("traces") or summary.get("n_traces") or summary.get("num_traces")
    gates = summary.get("gates") or summary.get("n_gates") or summary.get("num_gates")
    mean = summary.get("global_mean") or summary.get("mean")
    min_v = summary.get("global_min") or summary.get("min")
    max_v = summary.get("global_max") or summary.get("max")

    top_gates = summary.get("top_gates") or []
    if isinstance(top_gates, dict):
        # maybe {gate_id: value}
        top_gates = [
            {"gate_id": k, "value": v}
            for k, v in list(top_gates.items())[:5]
        ]
    elif isinstance(top_gates, list):
        # expect list of {gate_id, value, ...}
        top_gates = top_gates[:5]
    else:
        top_gates = []

    raw_snippet = _truncate_json(data)
    status = "G-field overlay present."
    return {
        "present": True,
        "status": status,
        "traces": traces,
        "gates": gates,
        "mean": mean,
        "min": min_v,
        "max": max_v,
        "top_gates": top_gates,
        "raw_snippet": raw_snippet,
    }


def summarise_g_field_stability(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not data:
        return {
            "present": False,
            "status": "No G-field stability overlay found.",
            "runs": None,
            "stable_gates": None,
            "unstable_gates": None,
            "unstable_list": [],
            "raw_snippet": "",
        }
    summary = data.get("summary") or {}
    runs = summary.get("runs") or summary.get("n_runs")
    stable = summary.get("stable_gates")
    unstable = summary.get("unstable_gates")
    unstable_list = summary.get("unstable_gate_ids") or summary.get("unstable") or []

    if isinstance(unstable_list, dict):
        unstable_list = list(unstable_list.keys())
    elif not isinstance(unstable_list, list):
        unstable_list = []

    raw_snippet = _truncate_json(data)

    if unstable and unstable > 0:
        status = f"{unstable} gates flagged as potentially unstable across {runs or '?'} runs."
    else:
        status = f"No unstable gates flagged across {runs or '?'} runs."

    return {
        "present": True,
        "status": status,
        "runs": runs,
        "stable_gates": stable,
        "unstable_gates": unstable,
        "unstable_list": unstable_list[:10],
        "raw_snippet": raw_snippet,
    }


def summarise_epf(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not data:
        return {
            "present": False,
            "status": "No G-EPF overlay found.",
            "total_gates": None,
            "in_band": None,
            "changed": None,
            "paradox": None,
            "shadow_pass": None,
            "paradox_panels": [],
            "raw_snippet": "",
        }
    summary = data.get("summary") or {}
    total = summary.get("total_gates")
    in_band = summary.get("gates_in_epf_band")
    changed = summary.get("gates_changed_by_epf")
    paradox = summary.get("gates_with_paradox_flag")
    shadow_pass = summary.get("shadow_pass")

    panels = data.get("panels") or []
    paradox_panels = []
    for p in panels:
        if not isinstance(p, dict):
            continue
        par = (p.get("paradox") or {})
        if par.get("has_paradox"):
            paradox_panels.append(
                {
                    "gate_id": p.get("gate_id"),
                    "baseline_decision": p.get("baseline_decision"),
                    "epf_shadow_decision": p.get("epf_shadow_decision"),
                    "severity": par.get("severity"),
                    "summary": par.get("summary"),
                }
            )
    paradox_panels = paradox_panels[:5]

    if paradox and paradox > 0:
        status = f"EPF overlay present; {paradox} paradox candidate gate(s) out of {total or '?'}."
    else:
        status = f"EPF overlay present; no paradox candidates across {total or '?'} gates."

    raw_snippet = _truncate_json(data)

    return {
        "present": True,
        "status": status,
        "total_gates": total,
        "in_band": in_band,
        "changed": changed,
        "paradox": paradox,
        "shadow_pass": shadow_pass,
        "paradox_panels": paradox_panels,
        "raw_snippet": raw_snippet,
    }


def summarise_gpt_external(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not data:
        return {
            "present": False,
            "status": "No GPT external detection overlay found.",
            "total_calls": None,
            "internal_calls": None,
            "external_calls": None,
            "external_share": None,
            "top_vendors": [],
            "raw_snippet": "",
        }

    # Try a few common patterns: summary.total_calls, stats.total, etc.
    summary = data.get("summary") or data.get("stats") or {}
    total = summary.get("total_calls") or summary.get("total")
    internal = summary.get("internal_calls") or summary.get("internal")
    external = summary.get("external_calls") or summary.get("external")

    external_share = None
    try:
        if total and external is not None:
            external_share = round(100.0 * float(external) / float(total), 2)
    except Exception:
        external_share = None

    top_vendors = summary.get("top_vendors") or summary.get("top_models") or []
    if isinstance(top_vendors, dict):
        # maybe {vendor: count}
        top_vendors = [
            {"vendor": k, "model": None, "calls": v}
            for k, v in list(top_vendors.items())[:5]
        ]
    elif isinstance(top_vendors, list):
        # expected shape: list of {vendor, model, calls}
        top_vendors = top_vendors[:5]
    else:
        top_vendors = []

    raw_snippet = _truncate_json(data)

    if total is None:
        status = "GPT external detection overlay present (no total_calls in summary)."
    elif external_share is None:
        status = f"GPT external detection overlay present; total calls: {total}."
    else:
        status = f"GPT external detection overlay present; total calls: {total}, external: {external_share}%."

    return {
        "present": True,
        "status": status,
        "total_calls": total,
        "internal_calls": internal,
        "external_calls": external,
        "external_share": external_share,
        "top_vendors": top_vendors,
        "raw_snippet": raw_snippet,
    }


def build_report() -> str:
    generated_at = _now_iso()

    g_field_data = _load_json_if_exists(G_FIELD_NAME)
    g_field_stab_data = _load_json_if_exists(G_FIELD_STAB_NAME)
    g_epf_data = _load_json_if_exists(G_EPF_NAME)
    gpt_ext_data = _load_json_if_exists(GPT_EXT_NAME)

    g_field = summarise_g_field(g_field_data)
    g_stab = summarise_g_field_stability(g_field_stab_data)
    epf = summarise_epf(g_epf_data)
    gpt = summarise_gpt_external(gpt_ext_data)

    lines = []

    lines.append("# G snapshot report v0 (shadow)")
    lines.append("")
    lines.append(f"Generated at: {generated_at}")
    lines.append("")
    lines.append("> This report is **shadow-only**. It never changes CI pass/fail or release")
    lines.append("> decisions. All signals here are diagnostic overlays on top of the")
    lines.append("> deterministic PULSE gates.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 0. Sources")
    lines.append("")
    lines.append("Legend: `[x]` = present, `[ ]` = not found in this run.")
    lines.append("")
    lines.append(f"- [{_checkbox(g_field['present'])}] G-field overlay (`{G_FIELD_NAME}`)")
    lines.append(f"- [{_checkbox(g_stab['present'])}] G-field stability overlay (`{G_FIELD_STAB_NAME}`)")
    lines.append(f"- [{_checkbox(epf['present'])}] G-EPF overlay (`{G_EPF_NAME}`)")
    lines.append(f"- [{_checkbox(gpt['present'])}] GPT external detection overlay (`{GPT_EXT_NAME}`)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. G-field overview")
    lines.append("")
    lines.append(f"**Status:** {g_field['status']}")
    lines.append("")
    if g_field["present"]:
        lines.append(f"- Traces covered: **{g_field['traces'] or 'N/A'}**")
        lines.append(f"- Gates covered: **{g_field['gates'] or 'N/A'}**")
        lines.append(f"- Global mean: **{g_field['mean'] if g_field['mean'] is not None else 'N/A'}**")
        lines.append(f"- Global min / max: **{g_field['min'] if g_field['min'] is not None else 'N/A'} / "
                     f"{g_field['max'] if g_field['max'] is not None else 'N/A'}**")
        lines.append("")
        if g_field["top_gates"]:
            lines.append("Top gates by absolute mean (up to 5):")
            lines.append("")
            lines.append("| Gate ID | Value |")
            lines.append("|---------|------:|")
            for g in g_field["top_gates"]:
                gate_id = g.get("gate_id") or g.get("id") or "?"
                value = g.get("value")
                lines.append(f"| {gate_id} | {value} |")
            lines.append("")
        lines.append("<details>")
        lines.append("<summary>Raw G-field snapshot (truncated)</summary>")
        lines.append("")
        lines.append("```json")
        lines.append(g_field["raw_snippet"])
        lines.append("```")
        lines.append("")
        lines.append("</details>")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. G-field stability")
    lines.append("")
    lines.append(f"**Status:** {g_stab['status']}")
    lines.append("")
    if g_stab["present"]:
        lines.append("- Runs aggregated: "
                     f"**{g_stab['runs'] if g_stab['runs'] is not None else 'N/A'}**")
        lines.append("- Gates flagged as potentially unstable: "
                     f"**{g_stab['unstable_gates'] if g_stab['unstable_gates'] is not None else '0'}**")
        lines.append("")
        if g_stab["unstable_list"]:
            lines.append("Unstable gates (up to 10):")
            lines.append("")
            lines.append("| Gate ID |")
            lines.append("|---------|")
            for gid in g_stab["unstable_list"]:
                lines.append(f"| {gid} |")
            lines.append("")
        lines.append("<details>")
        lines.append("<summary>Raw stability diagnostics (exact JSON, truncated)</summary>")
        lines.append("")
        lines.append("```json")
        lines.append(g_stab["raw_snippet"])
        lines.append("```")
        lines.append("")
        lines.append("</details>")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. G-EPF overlay (shadow)")
    lines.append("")
    lines.append(f"**Status:** {epf['status']}")
    lines.append("")
    if epf["present"]:
        lines.append(f"- Total gates in EPF overlay: **{epf['total_gates'] if epf['total_gates'] is not None else 'N/A'}**")
        lines.append(f"- Gates in EPF band: **{epf['in_band'] if epf['in_band'] is not None else 'N/A'}**")
        lines.append(f"- Gates changed by EPF (shadow): **{epf['changed'] if epf['changed'] is not None else 'N/A'}**")
        lines.append(f"- Gates with paradox flag: **{epf['paradox'] if epf['paradox'] is not None else '0'}**")
        lines.append(f"- Overall EPF shadow pass: **{epf['shadow_pass']}**")
        lines.append("")
        if epf["paradox_panels"]:
            lines.append("Paradox candidate gates (up to 5):")
            lines.append("")
            lines.append("| Gate ID | Baseline | EPF shadow | Severity | Summary |")
            lines.append("|---------|----------|------------|----------|---------|")
            for p in epf["paradox_panels"]:
                lines.append(
                    f"| {p.get('gate_id') or '?'} "
                    f"| {p.get('baseline_decision') or '?'} "
                    f"| {p.get('epf_shadow_decision') or '?'} "
                    f"| {p.get('severity') or '-'} "
                    f"| {p.get('summary') or ''} |"
                )
            lines.append("")
        lines.append("<details>")
        lines.append("<summary>Raw G-EPF overlay (truncated)</summary>")
        lines.append("")
        lines.append("```json")
        lines.append(epf["raw_snippet"])
        lines.append("```")
        lines.append("")
        lines.append("</details>")
    else:
        lines.append("> No `g_epf_overlay_v0.json` overlay was found. EPF overlays are optional,")
        lines.append("> shadow-only diagnostics and never change CI outcomes.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. GPT external usage (shadow)")
    lines.append("")
    lines.append(f"**Status:** {gpt['status']}")
    lines.append("")
    if gpt["present"]:
        lines.append(f"- Total GPT calls: **{gpt['total_calls'] if gpt['total_calls'] is not None else 'N/A'}**")
        lines.append(f"- Internal (HPC) calls: **{gpt['internal_calls'] if gpt['internal_calls'] is not None else 'N/A'}**")
        lines.append(f"- External calls: **{gpt['external_calls'] if gpt['external_calls'] is not None else 'N/A'}**")
        lines.append(f"- External share: **{gpt['external_share'] if gpt['external_share'] is not None else 'N/A'} %**")
        lines.append("")
        if gpt["top_vendors"]:
            lines.append("Top external vendors/models (up to 5):")
            lines.append("")
            lines.append("| Vendor | Model | Calls |")
            lines.append("|--------|-------|------:|")
            for v in gpt["top_vendors"]:
                vendor = v.get("vendor") or "?"
                model = v.get("model") or "-"
                calls = v.get("calls") if v.get("calls") is not None else "N/A"
                lines.append(f"| {vendor} | {model} | {calls} |")
            lines.append("")
        lines.append("<details>")
        lines.append("<summary>Raw GPT usage diagnostics (truncated)</summary>")
        lines.append("")
        lines.append("```json")
        lines.append(gpt["raw_snippet"])
        lines.append("```")
        lines.append("")
        lines.append("</details>")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 5. How to read this report")
    lines.append("")
    lines.append("- This report is **CI-neutral**: it does **not** participate in release gating.")
    lines.append("- All metrics are derived from the overlays listed in the *Sources* section.")
    lines.append("- When in doubt:")
    lines.append("  - treat G-field numbers as *diagnostic context* for the existing gates,")
    lines.append("  - treat stability flags as *hints* about robustness, not as hard pass/fail,")
    lines.append("  - treat EPF and GPT usage as *shadow overlays* for governance dashboards.")
    lines.append("")
    lines.append("For an end-to-end view of how these overlays are produced, see")
    lines.append("`docs/g_shadow_pipeline.md` and `docs/G_shadow_overlays_howto.md`.")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    PACK_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    output_path = PACK_ARTIFACTS / OUTPUT_NAME
    report = build_report()
    with output_path.open("w", encoding="utf-8") as f:
        f.write(report)
    print(f"[build_g_snapshot_report_v0] Wrote report to {output_path}")


if __name__ == "__main__":
    main()
