#!/usr/bin/env python3
"""
inspect_epf_shadow_v0.py

Action-first inspector for EPF shadow runs.

Given:
  - a deterministic baseline status JSON (status_baseline.json)
  - an EPF shadow status JSON (status_epf.json) [optional]

Emit:
  - a reviewer-friendly markdown summary (epf_shadow_summary_v0.md)
  - an optional machine-friendly diff JSON (epf_shadow_diff_v0.json)

Design goals:
  - deterministic output (stable ordering)
  - fail-closed for baseline input (required)
  - reviewer-friendly when EPF is missing (do not fail; explain)
  - schema-tolerant: supports multiple plausible status.json gate shapes
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple


EPF_STATE_NOT_PROVIDED = "not_provided"
EPF_STATE_MISSING_FILE = "missing_file"
EPF_STATE_PRESENT = "present"


# -----------------------------
# Models
# -----------------------------

@dataclass(frozen=True)
class GateInfo:
    gate_id: str
    decision: str  # PASS/FAIL/DEFER/UNKNOWN/...
    reason: str = ""
    value: Optional[float] = None
    threshold: Optional[float] = None


@dataclass(frozen=True)
class GateDiff:
    gate_id: str
    baseline: str
    epf: str
    delta: str  # e.g. PASS->FAIL
    baseline_reason: str = ""
    epf_reason: str = ""


# -----------------------------
# Helpers
# -----------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _ensure_parent_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def _to_str(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    return str(x)


def _as_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x))
    except Exception:
        return None


def _normalize_decision(x: Any) -> str:
    """
    Normalize a gate decision into a small canonical set when possible.
    """
    if x is None:
        return "UNKNOWN"

    if isinstance(x, bool):
        return "PASS" if x else "FAIL"

    if isinstance(x, (int, float)):
        # Avoid guessing semantics; treat numeric as UNKNOWN
        return "UNKNOWN"

    s = str(x).strip()
    if not s:
        return "UNKNOWN"

    u = s.upper()

    # Common boolean-ish strings
    if u in {"PASS", "PASSED", "OK", "TRUE", "YES", "ALLOW", "ALLOWED", "GREEN"}:
        return "PASS"
    if u in {"FAIL", "FAILED", "BLOCK", "FALSE", "NO", "DENY", "DENIED", "RED"}:
        return "FAIL"

    # EPF-ish / governance-ish states that can appear in shadow layers
    if u in {"DEFER", "DEFERRED"}:
        return "DEFER"
    if u in {"WARN", "WARNING", "AMBER", "YELLOW"}:
        return "WARN"

    return u


def _first_key(d: Dict[str, Any], keys: Iterable[str]) -> Any:
    for k in keys:
        if k in d:
            return d[k]
    return None


def _extract_reason(d: Dict[str, Any]) -> str:
    r = _first_key(d, ["reason", "message", "details", "explain", "note", "why"])
    return _to_str(r).strip()


def _extract_value_threshold(d: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    v = _as_float(_first_key(d, ["value", "metric", "score", "observed", "x"]))
    t = _as_float(_first_key(d, ["threshold", "min", "max", "target", "tau"]))
    return v, t


def _looks_like_gate_map(obj: Any) -> bool:
    if not isinstance(obj, dict) or not obj:
        return False
    # Keys look like IDs, values are bool/str/dict
    sample_k = next(iter(obj.keys()))
    if not isinstance(sample_k, str):
        return False
    sample_v = obj[sample_k]
    return isinstance(sample_v, (bool, str, dict, int, float, list))


def _extract_gate_infos(status: Any) -> Dict[str, GateInfo]:
    """
    Try to extract a normalized gate_id -> GateInfo map from a status.json-like object.
    Supports:
      - status["gates"] as dict: {gate_id: bool|str|dict}
      - status["gates"] as list: [{"gate": "...", "pass": true, ...}, ...]
      - status["gate_results"] / status["checks"] / status["results"] if present
    """
    if not isinstance(status, dict):
        return {}

    # Candidate containers in order of preference
    candidates: List[Any] = []
    for key in ["gates", "gate_results", "checks", "results"]:
        if key in status:
            candidates.append(status[key])

    # If nothing obvious, try heuristics on top-level keys
    if not candidates:
        for k, v in status.items():
            if k.lower() in {"gates", "gate_results", "checks", "results"}:
                candidates.append(v)

    gate_map: Dict[str, GateInfo] = {}

    def add_gate(
        gate_id_raw: Any,
        decision_raw: Any,
        reason: str = "",
        value: Optional[float] = None,
        threshold: Optional[float] = None,
    ) -> None:
        gid = _to_str(gate_id_raw).strip()
        if not gid:
            return
        decision = _normalize_decision(decision_raw)
        gate_map[gid] = GateInfo(
            gate_id=gid,
            decision=decision,
            reason=reason,
            value=value,
            threshold=threshold,
        )

    def handle_dict(container: Dict[str, Any]) -> None:
        for gid, v in container.items():
            if isinstance(v, (bool, str)):
                add_gate(gid, v)
                continue

            if isinstance(v, dict):
                decision_raw = _first_key(
                    v,
                    [
                        "pass",
                        "ok",
                        "allowed",
                        "allow",
                        "success",
                        "passed",
                        "decision",
                        "status",
                        "state",
                        "result",
                    ],
                )
                reason = _extract_reason(v)
                value, threshold = _extract_value_threshold(v)
                add_gate(gid, decision_raw, reason=reason, value=value, threshold=threshold)
                continue

            add_gate(gid, None)

    def handle_list(container: List[Any]) -> None:
        for item in container:
            if not isinstance(item, dict):
                continue
            gid = _first_key(item, ["gate", "gate_id", "id", "name", "key"])
            decision_raw = _first_key(
                item,
                [
                    "pass",
                    "ok",
                    "allowed",
                    "allow",
                    "success",
                    "passed",
                    "decision",
                    "status",
                    "state",
                    "result",
                ],
            )
            reason = _extract_reason(item)
            value, threshold = _extract_value_threshold(item)
            add_gate(gid, decision_raw, reason=reason, value=value, threshold=threshold)

    for c in candidates:
        if isinstance(c, dict) and _looks_like_gate_map(c):
            handle_dict(c)
            if gate_map:
                break
        if isinstance(c, list) and c:
            handle_list(c)
            if gate_map:
                break

    if not gate_map:
        for k, v in status.items():
            if isinstance(v, dict) and any(x in v for x in ["pass", "ok", "decision", "status", "state"]):
                decision_raw = _first_key(v, ["pass", "ok", "decision", "status", "state"])
                reason = _extract_reason(v)
                value, threshold = _extract_value_threshold(v)
                add_gate(k, decision_raw, reason=reason, value=value, threshold=threshold)

    return gate_map


def _summarize_metrics(status: Any, keys: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not isinstance(status, dict):
        return out
    metrics = status.get("metrics")
    if not isinstance(metrics, dict):
        return out
    for k in keys:
        if k in metrics:
            out[k] = metrics[k]
    return out


def _diff_gates(
    baseline: Dict[str, GateInfo],
    epf: Dict[str, GateInfo],
) -> Tuple[List[GateDiff], List[str], List[str]]:
    baseline_ids = set(baseline.keys())
    epf_ids = set(epf.keys())

    missing_in_epf = sorted(baseline_ids - epf_ids)
    missing_in_baseline = sorted(epf_ids - baseline_ids)

    diffs: List[GateDiff] = []
    for gid in sorted(baseline_ids & epf_ids):
        b = baseline[gid]
        e = epf[gid]
        if b.decision != e.decision:
            diffs.append(
                GateDiff(
                    gate_id=gid,
                    baseline=b.decision,
                    epf=e.decision,
                    delta=f"{b.decision}->{e.decision}",
                    baseline_reason=b.reason,
                    epf_reason=e.reason,
                )
            )

    def severity_rank(d: GateDiff) -> Tuple[int, str]:
        if d.delta == "PASS->FAIL":
            return (0, d.gate_id)
        if d.delta == "FAIL->PASS":
            return (1, d.gate_id)
        return (2, d.gate_id)

    diffs = sorted(diffs, key=severity_rank)
    return diffs, missing_in_epf, missing_in_baseline


def _count_by_delta(diffs: List[GateDiff]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for d in diffs:
        out[d.delta] = out.get(d.delta, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (kv[0])))


def _render_markdown(
    baseline_path: str,
    epf_path: Optional[str],
    epf_state: str,
    baseline_gates: Dict[str, GateInfo],
    epf_gates: Dict[str, GateInfo],
    diffs: List[GateDiff],
    missing_in_epf: List[str],
    missing_in_baseline: List[str],
    baseline_metrics: Dict[str, Any],
    epf_metrics: Dict[str, Any],
    max_rows: int,
    include_timestamp: bool,
) -> str:
    lines: List[str] = []
    lines.append("# EPF shadow summary v0")
    lines.append("")
    lines.append("## Inputs")
    lines.append(f"- baseline: `{baseline_path}`")

    if epf_state == EPF_STATE_NOT_PROVIDED:
        lines.append("- epf: _(not provided)_")
    elif epf_state == EPF_STATE_MISSING_FILE:
        lines.append(f"- epf: `{epf_path}` _(missing file)_")
    else:
        lines.append(f"- epf: `{epf_path}`")

    lines.append("")
    lines.append("## Summary")
    lines.append(f"- baseline gates: **{len(baseline_gates)}**")

    if epf_state == EPF_STATE_PRESENT:
        lines.append(f"- epf gates: **{len(epf_gates)}**")
        lines.append(f"- changed gates: **{len(diffs)}**")
    else:
        lines.append("- epf gates: _(not computed)_")
        lines.append("- changed gates: _(not computed)_")

    if epf_state == EPF_STATE_MISSING_FILE:
        lines.append("")
        lines.append(f"> ⚠️ EPF input was requested but the file was not found: `{epf_path}`")
        lines.append("> Comparison skipped (baseline extracted only).")
    elif epf_state == EPF_STATE_PRESENT and epf_path and not epf_gates:
        lines.append("")
        lines.append("> ⚠️ EPF file was provided, but no gates could be extracted from it.")
        lines.append("> This likely means the status format differs from expectations (schema drift) or the file is empty.")
    elif epf_state == EPF_STATE_NOT_PROVIDED:
        lines.append("")
        lines.append("> ℹ️ No EPF input provided. This report is informational only (baseline extracted).")

    lines.append("")

    if baseline_metrics or (epf_state == EPF_STATE_PRESENT and epf_metrics):
        lines.append("## Key metrics (optional)")
        if baseline_metrics:
            lines.append("- baseline metrics:")
            for k in sorted(baseline_metrics.keys()):
                lines.append(f"  - `{k}`: `{baseline_metrics[k]}`")
        if epf_state == EPF_STATE_PRESENT and epf_metrics:
            lines.append("- epf metrics:")
            for k in sorted(epf_metrics.keys()):
                lines.append(f"  - `{k}`: `{epf_metrics[k]}`")
        lines.append("")

    if epf_state != EPF_STATE_PRESENT:
        lines.append("## Gate diffs")
        lines.append("")
        if epf_state == EPF_STATE_MISSING_FILE:
            lines.append("_EPF file missing; comparison not performed._")
        else:
            lines.append("_No EPF input provided; comparison not performed._")
        lines.append("")
    else:
        if diffs:
            by_delta = _count_by_delta(diffs)
            lines.append("## Delta breakdown")
            for k in sorted(by_delta.keys()):
                lines.append(f"- `{k}`: **{by_delta[k]}**")
            lines.append("")

            lines.append("## Gate diffs (top)")
            lines.append("")
            lines.append("| gate_id | baseline | epf | delta | baseline_reason | epf_reason |")
            lines.append("|---|---:|---:|---:|---|---|")

            shown = 0
            for d in diffs:
                if shown >= max_rows:
                    break
                br = d.baseline_reason.replace("\n", " ").strip()
                er = d.epf_reason.replace("\n", " ").strip()
                lines.append(f"| `{d.gate_id}` | `{d.baseline}` | `{d.epf}` | `{d.delta}` | {br} | {er} |")
                shown += 1

            if len(diffs) > max_rows:
                lines.append("")
                lines.append(f"> Showing first **{max_rows}** diffs. Increase `--max-rows` for more.")
            lines.append("")
        else:
            lines.append("## Gate diffs")
            lines.append("")
            lines.append("_No gate decision differences detected between baseline and EPF._")
            lines.append("")

        if missing_in_epf:
            lines.append("## Gates missing in EPF")
            lines.append("")
            lines.append(f"_Present in baseline, missing in EPF: **{len(missing_in_epf)}**_")
            lines.append("")
            for gid in missing_in_epf[:max_rows]:
                lines.append(f"- `{gid}`")
            if len(missing_in_epf) > max_rows:
                lines.append(f"- ... (+{len(missing_in_epf) - max_rows} more)")
            lines.append("")

        if missing_in_baseline:
            lines.append("## Gates missing in baseline")
            lines.append("")
            lines.append(f"_Present in EPF, missing in baseline: **{len(missing_in_baseline)}**_")
            lines.append("")
            for gid in missing_in_baseline[:max_rows]:
                lines.append(f"- `{gid}`")
            if len(missing_in_baseline) > max_rows:
                lines.append(f"- ... (+{len(missing_in_baseline) - max_rows} more)")
            lines.append("")

    lines.append("## How to interpret")
    lines.append("")
    lines.append("EPF is a **shadow** signal layer: disagreements are a prompt to investigate, not an automatic ship/block.")
    lines.append("See: `docs/epf_primer_v0.md`.")
    lines.append("")

    lines.append("## Determinism")
    lines.append("")
    lines.append("This report is deterministic given identical input JSON files:")
    lines.append("- stable sorting of gate IDs")
    lines.append("- stable ordering of deltas (PASS→FAIL first, then FAIL→PASS, then others)")
    lines.append("- timestamp omitted by default (use `--include-timestamp` to include one)")
    lines.append("")

    if include_timestamp:
        lines.append(f"_Generated: `{_utc_now_iso()}`_")
    else:
        lines.append("_Generated by `scripts/inspect_epf_shadow_v0.py` (timestamp omitted for deterministic diffs)._")
    lines.append("")

    return "\n".join(lines)


def _render_diff_json(
    baseline_path: str,
    epf_path: Optional[str],
    epf_state: str,
    diffs: List[GateDiff],
    missing_in_epf: List[str],
    missing_in_baseline: List[str],
    baseline_metrics: Dict[str, Any],
    epf_metrics: Dict[str, Any],
    include_timestamp: bool,
) -> Dict[str, Any]:
    return {
        "schema_version": "epf_shadow_diff_v0",
        "generated_utc": _utc_now_iso() if include_timestamp else None,
        "inputs": {
            "baseline": baseline_path,
            "epf": epf_path,
            "epf_state": epf_state,
        },
        "comparison_performed": (epf_state == EPF_STATE_PRESENT),
        "counts": {
            "changed_gates": len(diffs),
            "missing_in_epf": len(missing_in_epf),
            "missing_in_baseline": len(missing_in_baseline),
        },
        "delta_counts": _count_by_delta(diffs),
        "missing": {
            "in_epf": missing_in_epf,
            "in_baseline": missing_in_baseline,
        },
        "metrics": {
            "baseline": baseline_metrics,
            "epf": epf_metrics,
        },
        "diffs": [
            {
                "gate_id": d.gate_id,
                "baseline": d.baseline,
                "epf": d.epf,
                "delta": d.delta,
                "baseline_reason": d.baseline_reason,
                "epf_reason": d.epf_reason,
            }
            for d in diffs
        ],
    }


# -----------------------------
# CLI
# -----------------------------

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Inspect EPF shadow vs baseline status JSON and emit a deterministic diff summary."
    )
    p.add_argument("--baseline", required=True, help="Path to baseline status JSON (e.g., out/status_baseline.json).")
    p.add_argument("--epf", default=None, help="Path to EPF shadow status JSON (optional; if missing, report explains).")
    p.add_argument("--out-md", required=True, help="Path to output markdown summary (e.g., out/epf_shadow_summary_v0.md).")
    p.add_argument("--out-json", default=None, help="Optional path to output diff JSON (e.g., out/epf_shadow_diff_v0.json).")
    p.add_argument("--max-rows", type=int, default=50, help="Max rows to print in markdown tables/lists.")
    p.add_argument("--include-timestamp", action="store_true", help="Include generation timestamp in outputs (disables strict determinism).")
    args = p.parse_args(argv)

    baseline_path = args.baseline
    epf_path = args.epf
    out_md = args.out_md
    out_json = args.out_json
    max_rows = int(args.max_rows)
    include_timestamp = bool(args.include_timestamp)

    if not os.path.isfile(baseline_path):
        print(f"[inspect_epf_shadow_v0] ERROR: baseline file not found: {baseline_path}", file=sys.stderr)
        return 2

    try:
        baseline_status = _read_json(baseline_path)
    except Exception as e:
        print(f"[inspect_epf_shadow_v0] ERROR: failed to parse baseline JSON: {baseline_path}\n{e}", file=sys.stderr)
        return 2

    epf_status: Any = None
    if not epf_path:
        epf_state = EPF_STATE_NOT_PROVIDED
    elif not os.path.isfile(epf_path):
        epf_state = EPF_STATE_MISSING_FILE
    else:
        epf_state = EPF_STATE_PRESENT
        try:
            epf_status = _read_json(epf_path)
        except Exception as e:
            print(f"[inspect_epf_shadow_v0] ERROR: failed to parse EPF JSON: {epf_path}\n{e}", file=sys.stderr)
            return 2

    baseline_gates = _extract_gate_infos(baseline_status)
    epf_gates = _extract_gate_infos(epf_status) if epf_state == EPF_STATE_PRESENT else {}

    baseline_metrics = _summarize_metrics(
        baseline_status,
        keys=["epf_L", "hazard_E", "hazard_zone", "hazard_ok", "hazard_severity"],
    )
    epf_metrics = _summarize_metrics(
        epf_status,
        keys=["epf_L", "hazard_E", "hazard_zone", "hazard_ok", "hazard_severity"],
    ) if epf_state == EPF_STATE_PRESENT else {}

    diffs: List[GateDiff] = []
    missing_in_epf: List[str] = []
    missing_in_baseline: List[str] = []

    if epf_state == EPF_STATE_PRESENT:
        diffs, missing_in_epf, missing_in_baseline = _diff_gates(baseline_gates, epf_gates)

    md = _render_markdown(
        baseline_path=baseline_path,
        epf_path=epf_path if epf_path else None,
        epf_state=epf_state,
        baseline_gates=baseline_gates,
        epf_gates=epf_gates,
        diffs=diffs,
        missing_in_epf=missing_in_epf,
        missing_in_baseline=missing_in_baseline,
        baseline_metrics=baseline_metrics,
        epf_metrics=epf_metrics,
        max_rows=max_rows,
        include_timestamp=include_timestamp,
    )

    _ensure_parent_dir(out_md)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)

    if out_json:
        payload = _render_diff_json(
            baseline_path=baseline_path,
            epf_path=epf_path if epf_path else None,
            epf_state=epf_state,
            diffs=diffs,
            missing_in_epf=missing_in_epf,
            missing_in_baseline=missing_in_baseline,
            baseline_metrics=baseline_metrics,
            epf_metrics=epf_metrics,
            include_timestamp=include_timestamp,
        )
        _ensure_parent_dir(out_json)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")

    print(f"[inspect_epf_shadow_v0] wrote: {out_md}")
    if out_json:
        print(f"[inspect_epf_shadow_v0] wrote: {out_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

