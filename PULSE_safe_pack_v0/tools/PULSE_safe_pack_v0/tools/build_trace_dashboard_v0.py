#!/usr/bin/env python
"""
build_trace_dashboard_v0.py

Shadow-only dashboard builder on top of:

- decision_history_v0.json
- paradox_history_v0.json

The goal is to produce a compact "trace_dashboard_v0.json" that
summarises:

- decision history per run (decision, type, instability, paradox zone),
- paradox axes history (which axes are dominant / severe).
"""

import argparse
import json
from typing import Any, Dict, List, Optional


Json = Dict[str, Any]


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_decision_overview(
    decision_history: Any,
    max_runs: Optional[int],
) -> Json:
    """
    Build a compact decision overview section.

    The tool is defensive: it accepts either

    - {"runs": [...]}  or
    - a bare list  or
    - a single run dict.

    It keeps only the last `max_runs` entries if specified.
    """
    # Normalise to list of dicts
    if isinstance(decision_history, dict) and isinstance(
        decision_history.get("runs"), list
    ):
        runs = decision_history["runs"]
    elif isinstance(decision_history, list):
        runs = decision_history
    else:
        runs = [decision_history]

    # Keep last max_runs if requested
    if max_runs is not None and max_runs >= 0:
        runs = runs[-max_runs:]

    out_runs: List[Json] = []

    for r in runs:
        if not isinstance(r, dict):
            continue

        out_runs.append(
            {
                "run_id": r.get("run_id"),
                "decision": r.get("decision"),
                "type": r.get("type"),
                # instability key may be "instability_score" or "instability"
                "instability": r.get("instability_score", r.get("instability")),
                "paradox_zone": r.get("paradox_zone"),
                "rdsi": r.get("rdsi"),
            }
        )

    return {"runs": out_runs}


def _severity_rank(severity: Optional[str]) -> int:
    order = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
        None: 0,
    }
    return order.get(severity, 0)


def _build_paradox_overview(
    paradox_history: Any,
    top_axes: Optional[int],
) -> Json:
    """
    Build a compact paradox overview section.

    Expects either:

    - {"axes": [...]}  or
    - a bare list  of axis entries.

    Each axis entry may contain:

    - axis_id
    - runs_seen
    - times_dominant
    - severity
    - recommended_focus_latest (or recommended_focus)
    """
    if isinstance(paradox_history, dict) and isinstance(
        paradox_history.get("axes"), list
    ):
        axes = paradox_history["axes"]
    elif isinstance(paradox_history, list):
        axes = paradox_history
    else:
        axes = []

    norm_axes: List[Json] = [a for a in axes if isinstance(a, dict)]

    def _score(a: Json) -> tuple:
        return (
            _severity_rank(a.get("severity")),
            a.get("times_dominant") or 0,
            a.get("runs_seen") or 0,
        )

    norm_axes.sort(key=_score, reverse=True)

    if top_axes is not None and top_axes >= 0:
        norm_axes = norm_axes[:top_axes]

    out_axes: List[Json] = []

    for a in norm_axes:
        out_axes.append(
            {
                "axis_id": a.get("axis_id"),
                "runs_seen": a.get("runs_seen"),
                "times_dominant": a.get("times_dominant"),
                "severity": a.get("severity"),
                "recommended_focus_latest": (
                    a.get("recommended_focus_latest") or a.get("recommended_focus")
                ),
            }
        )

    return {"top_axes": out_axes}


def build_trace_dashboard(
    decision_history_path: str,
    paradox_history_path: str,
    out_path: str,
    max_runs: Optional[int],
    top_axes: Optional[int],
) -> None:
    decision_history = _load_json(decision_history_path)
    paradox_history = _load_json(paradox_history_path)

    dashboard: Json = {
        "version": "0.1",
        "source": {
            "decision_history": decision_history_path,
            "paradox_history": paradox_history_path,
        },
        "decision_overview": _build_decision_overview(
            decision_history, max_runs
        ),
        "paradox_overview": _build_paradox_overview(
            paradox_history, top_axes
        ),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, indent=2, sort_keys=False)

    print(f"[trace-dashboard] wrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build trace_dashboard_v0.json from decision & paradox history."
    )
    parser.add_argument(
        "--decision-history",
        required=True,
        help="Path to decision_history_v0.json",
    )
    parser.add_argument(
        "--paradox-history",
        required=True,
        help="Path to paradox_history_v0.json",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=50,
        help="Max number of most recent runs to include (default: 50, use -1 for all).",
    )
    parser.add_argument(
        "--top-axes",
        type=int,
        default=10,
        help="Max number of paradox axes to include (default: 10, use -1 for all).",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output path for trace_dashboard_v0.json",
    )

    args = parser.parse_args()

    max_runs = None if args.max_runs is not None and args.max_runs < 0 else args.max_runs
    top_axes = None if args.top_axes is not None and args.top_axes < 0 else args.top_axes

    build_trace_dashboard(
        decision_history_path=args.decision_history,
        paradox_history_path=args.paradox_history,
        out_path=args.out,
        max_runs=max_runs,
        top_axes=top_axes,
    )


if __name__ == "__main__":
    main()
