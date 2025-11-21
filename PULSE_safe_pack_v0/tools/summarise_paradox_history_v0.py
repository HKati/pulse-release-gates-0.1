#!/usr/bin/env python
"""
summarise_paradox_history_v0.py

Aggregate multiple decision_paradox_summary_v0.json files into a single
history view of paradox and EPF fields across runs.

Input:
    - a directory with one or more decision_paradox_summary_v0*.json files
      (produced by summarise_decision_paradox_v0.py)

Output:
    - paradox_history_v0.json (by default), containing:
        - per-run records (decision, instability, paradox zone, EPF snapshot)
        - aggregated paradox stats per axis
        - aggregated EPF stats (min/max/avg)
"""

import argparse
import glob
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


Summary = Dict[str, Any]
History = Dict[str, Any]


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _zone_from_tension(t: Optional[float]) -> str:
    if t is None:
        return "unknown"
    if t >= 0.66:
        return "red"
    if t >= 0.33:
        return "yellow"
    return "green"


def _avg(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    return sum(vals) / len(vals)


def _compute_risk_score_and_zone(
    instability_score: Optional[float], rdsi: Optional[float]
) -> Tuple[Optional[float], str]:
    if instability_score is None or rdsi is None:
        return None, "UNKNOWN"

    try:
        inst = float(instability_score)
        r = float(rdsi)
    except (TypeError, ValueError):
        return None, "UNKNOWN"

    raw = inst * (1.0 - r)
    risk = max(0.0, min(1.0, raw))

    if risk < 0.25:
        return risk, "LOW"
    if risk < 0.50:
        return risk, "MEDIUM"
    if risk < 0.75:
        return risk, "HIGH"
    return risk, "CRITICAL"


def load_summaries(dir_path: str, pattern: str) -> List[Summary]:
    glob_pattern = os.path.join(dir_path, pattern)
    paths = sorted(glob.glob(glob_pattern))
    summaries: List[Summary] = []

    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                summaries.append(json.load(f))
        except (OSError, json.JSONDecodeError):
            # v0: csendben kihagyjuk a hibás fájlokat
            continue

    return summaries


def build_paradox_history_v0(summaries: List[Summary]) -> History:
    runs: List[Dict[str, Any]] = []
    zone_counts: Dict[str, int] = {"green": 0, "yellow": 0, "red": 0, "unknown": 0}
    max_tension_overall: float = 0.0

    axis_stats: Dict[str, Dict[str, Any]] = {}

    phi_vals: List[float] = []
    theta_vals: List[float] = []
    risk_vals: List[float] = []
    risk_zone_counts: Dict[str, int] = {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0,
        "UNKNOWN": 0,
    }

    for s in summaries:
        if not isinstance(s, dict):
            continue

        run_id = s.get("run_id")
        decision = s.get("decision")
        type_ = s.get("type")

        stability = s.get("stability") or {}
        instab = _safe_float(stability.get("instability_score"))
        rdsi = _safe_float(stability.get("rdsi"))
        risk_score = _safe_float(stability.get("risk_score_v0"))
        risk_zone = stability.get("risk_zone")

        # Compute risk if missing or malformed
        if risk_score is None or not isinstance(risk_zone, str):
            risk_score, risk_zone = _compute_risk_score_and_zone(instab, rdsi)

        paradox = s.get("paradox_overview") or {}
        max_tension = _safe_float(paradox.get("max_tension"))
        zone = _zone_from_tension(max_tension)

        axes_list = paradox.get("axes") or []
        dominant_axes = paradox.get("dominant_axes") or []

        epf = s.get("epf_overview") or {}
        phi = _safe_float(epf.get("phi_potential"))
        theta = _safe_float(epf.get("theta_distortion"))

        runs.append(
            {
                "run_id": run_id,
                "decision": decision,
                "type": type_,
                "instability_score": instab,
                "paradox_zone": zone,
                "paradox_max_tension": max_tension,
                "epf_phi_potential": phi,
                "epf_theta_distortion": theta,
                "dominant_axes": dominant_axes,
                "risk_score_v0": risk_score,
                "risk_zone": risk_zone,
            }
        )

        zone_counts[zone] = zone_counts.get(zone, 0) + 1

        if risk_zone:
            risk_zone_counts[risk_zone] = risk_zone_counts.get(risk_zone, 0) + 1
        if risk_score is not None:
            risk_vals.append(risk_score)

        if max_tension is not None and max_tension > max_tension_overall:
            max_tension_overall = max_tension

        # tengely szintű aggregáció
        for ax in axes_list:
            if not isinstance(ax, dict):
                continue
            axis_id = ax.get("axis_id")
            if not axis_id:
                continue

            t = _safe_float(ax.get("max_tension")) or 0.0

            stat = axis_stats.setdefault(
                axis_id,
                {
                    "axis_id": axis_id,
                    "runs_seen": 0,
                    "times_dominant": 0,
                    "max_tension": 0.0,
                    "sum_tension": 0.0,
                },
            )

            stat["runs_seen"] += 1
            stat["sum_tension"] += t
            if t > stat["max_tension"]:
                stat["max_tension"] = t
            if axis_id in dominant_axes:
                stat["times_dominant"] += 1

        if phi is not None:
            phi_vals.append(phi)
        if theta is not None:
            theta_vals.append(theta)

    # tengely statusz lista
    axes_out: List[Dict[str, Any]] = []
    for axis_id, stat in axis_stats.items():
        runs_seen = stat["runs_seen"]
        avg_tension = (
            stat["sum_tension"] / runs_seen if runs_seen > 0 else None
        )
        axes_out.append(
            {
                "axis_id": axis_id,
                "runs_seen": runs_seen,
                "times_dominant": stat["times_dominant"],
                "max_tension": stat["max_tension"],
                "avg_tension": avg_tension,
            }
        )

    axes_out.sort(key=lambda a: a["max_tension"], reverse=True)

    epf_history = {
        "phi_potential": {
            "min": min(phi_vals) if phi_vals else None,
            "max": max(phi_vals) if phi_vals else None,
            "avg": _avg(phi_vals),
        },
        "theta_distortion": {
            "min": min(theta_vals) if theta_vals else None,
            "max": max(theta_vals) if theta_vals else None,
            "avg": _avg(theta_vals),
        },
    }

    risk_history = {
        "min": min(risk_vals) if risk_vals else None,
        "max": max(risk_vals) if risk_vals else None,
        "avg": _avg(risk_vals),
        "zone_counts": risk_zone_counts,
    }

    history: History = {
        "version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "num_runs": len(runs),
        "runs": runs,
        "paradox_history": {
            "max_tension_overall": max_tension_overall,
            "zone_counts": zone_counts,
            "axes": axes_out,
        },
        "epf_history": epf_history,
        "risk_history": risk_history,
    }

    return history


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarise paradox history across runs."
    )

    # New shorthand form: --input-glob / --output
    parser.add_argument(
        "--input",
        "--input-glob",
        dest="input_glob",
        help=(
            "Glob for decision_paradox_summary_v0*.json, e.g. "
            "'./artifacts/decision_paradox_summary_v0*.json'. "
            "If set, this is split into --dir and --pattern."
        ),
    )

    # Legacy form: --dir / --pattern / --out
    parser.add_argument(
        "--dir",
        "--input-dir",
        dest="dir",
        default=".",
        help="Directory containing decision_paradox_summary_v0*.json files.",
    )

    parser.add_argument(
        "--pattern",
        "--input-pattern",
        dest="pattern",
        default="decision_paradox_summary_v0*.json",
        help="Glob pattern for per-run summary files.",
    )

    parser.add_argument(
        "--out",
        "--output",
        dest="out",
        default="paradox_history_v0.json",
        help="Output file for aggregated history JSON.",
    )

    args = parser.parse_args()

    if getattr(args, "input_glob", None):
        dir_name, pattern = os.path.split(args.input_glob)
        if dir_name:
            args.dir = dir_name
        if pattern:
            args.pattern = pattern

    return args



def main() -> None:
    args = _parse_args()

    summaries = load_summaries(args.dir, args.pattern)
    history = build_paradox_history_v0(summaries)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, sort_keys=True)

    print(
        f"[paradox_history_v0] aggregated {history['num_runs']} runs "
        f"into {args.out}"
    )


if __name__ == "__main__":
    main()

