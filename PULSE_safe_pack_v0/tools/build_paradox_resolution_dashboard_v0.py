#!/usr/bin/env python
"""
build_paradox_resolution_dashboard_v0.py

Paradox Resolution dashboard v0 – shadow-only dashboard view.

Input:
    - paradox_resolution_v0.json
      (produced by build_paradox_resolution_v0.py)

Output:
    - paradox_resolution_dashboard_v0.json (by default), containing:
        - summary (num_axes, severity_counts, num_runs_considered)
        - axes[] sorted by priority and max_tension, each with a headline

This tool does NOT change any gate logic. It is a derived, human-facing
view on top of the resolution plan.
"""

import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


ResolutionPlan = Dict[str, Any]
Dashboard = Dict[str, Any]


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _build_headline(axis: Dict[str, Any]) -> str:
    axis_id = axis.get("axis_id")
    severity = axis.get("severity")
    priority = axis.get("priority")
    runs_seen = axis.get("runs_seen")
    times_dominant = axis.get("times_dominant")
    max_tension = _safe_float(axis.get("max_tension"))
    avg_tension = _safe_float(axis.get("avg_tension"))

    parts = [
        f"P{priority}",
        f"severity={severity}",
        f"axis={axis_id}",
        f"runs_seen={runs_seen}",
        f"dominant={times_dominant}",
        f"max_tension={max_tension}",
        f"avg_tension={avg_tension}",
    ]
    return " | ".join(str(p) for p in parts)


def build_paradox_resolution_dashboard_v0(
    plan: ResolutionPlan, top_n: Optional[int] = None
) -> Dashboard:
    """
    Build a dashboard-style view from paradox_resolution_v0.json.

    - Sort axes by (priority ASC, max_tension DESC).
    - Optionally keep only top_n axes.
    - Add a human-readable headline per axis.
    """
    axes_in = plan.get("axes") or []
    if not isinstance(axes_in, list):
        axes_in = []

    # rendezés: priority (nő), majd max_tension (csökken)
    def _sort_key(ax: Dict[str, Any]):
        priority = int(ax.get("priority", 999))
        max_t = _safe_float(ax.get("max_tension")) or 0.0
        return (priority, -max_t)

    axes_sorted = sorted(
        [ax for ax in axes_in if isinstance(ax, dict)],
        key=_sort_key,
    )

    if top_n is not None and top_n > 0:
        axes_sorted = axes_sorted[:top_n]

    axes_out: List[Dict[str, Any]] = []
    for ax in axes_sorted:
        axis_id = ax.get("axis_id")
        severity = ax.get("severity")
        priority = ax.get("priority")
        runs_seen = int(ax.get("runs_seen", 0))
        times_dominant = int(ax.get("times_dominant", 0))
        max_tension = _safe_float(ax.get("max_tension"))
        avg_tension = _safe_float(ax.get("avg_tension"))
        recommended_focus = ax.get("recommended_focus") or []

        axes_out.append(
            {
                "axis_id": axis_id,
                "severity": severity,
                "priority": priority,
                "runs_seen": runs_seen,
                "times_dominant": times_dominant,
                "max_tension": max_tension,
                "avg_tension": avg_tension,
                "recommended_focus": recommended_focus,
                "headline": _build_headline(ax),
            }
        )

    summary_in = plan.get("summary") or {}
    num_runs = plan.get("num_runs_considered")

    dashboard: Dashboard = {
        "version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "num_axes": len(axes_out),
        "num_runs_considered": num_runs,
        "summary": {
            "severity_counts": summary_in.get("severity_counts") or {},
        },
        "axes": axes_out,
    }

    return dashboard


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build paradox_resolution_dashboard_v0.json from "
            "paradox_resolution_v0.json"
        )
    )
    parser.add_argument(
        "--resolution",
        dest="resolution_path",
        default="paradox_resolution_v0.json",
        help=(
            "Path to paradox_resolution_v0.json "
            "(default: ./paradox_resolution_v0.json)"
        ),
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        default="paradox_resolution_dashboard_v0.json",
        help=(
            "Output JSON path "
            "(default: ./paradox_resolution_dashboard_v0.json)"
        ),
    )
    parser.add_argument(
        "--top-n",
        dest="top_n",
        type=int,
        default=None,
        help="If set, keep only the top N axes in the dashboard.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    with open(args.resolution_path, "r", encoding="utf-8") as f:
        plan: ResolutionPlan = json.load(f)

    dashboard = build_paradox_resolution_dashboard_v0(plan, top_n=args.top_n)

    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)

    print(
        f"[paradox_resolution_dashboard_v0] wrote "
        f"{dashboard['num_axes']} axes into {args.out_path}"
    )


if __name__ == "__main__":
    main()
