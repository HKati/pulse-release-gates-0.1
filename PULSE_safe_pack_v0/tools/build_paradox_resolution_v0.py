#!/usr/bin/env python
"""
build_paradox_resolution_v0.py

Paradox Resolution v0 – shadow-only resolution plan builder.

Input:
    - paradox_history_v0.json
      (produced by summarise_paradox_history_v0.py)

Output:
    - paradox_resolution_v0.json (by default), containing:
        - per-axis severity and priority
        - suggested focus areas and generic recommendations

This tool does NOT change any gate logic. It is a separate artefact
to support human triage / planning.
"""

import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


History = Dict[str, Any]
ResolutionPlan = Dict[str, Any]


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _classify_severity(max_tension: Optional[float],
                       avg_tension: Optional[float],
                       runs_seen: int,
                       times_dominant: int) -> str:
    """
    Simple v0 severity heuristic:

    - CRITICAL:
        - max_tension >= 0.8 and times_dominant >= 2, or
        - max_tension >= 0.8 and runs_seen >= 3
    - HIGH:
        - max_tension >= 0.66, or
        - avg_tension >= 0.5
    - MEDIUM:
        - max_tension >= 0.33
    - LOW:
        - otherwise
    """
    mt = max_tension or 0.0
    at = avg_tension or 0.0

    if (mt >= 0.8 and times_dominant >= 2) or (mt >= 0.8 and runs_seen >= 3):
        return "CRITICAL"
    if mt >= 0.66 or at >= 0.5:
        return "HIGH"
    if mt >= 0.33:
        return "MEDIUM"
    return "LOW"


def _priority_from_severity(severity: str) -> int:
    """
    Map severity to a simple numeric priority (1 = highest).
    """
    if severity == "CRITICAL":
        return 1
    if severity == "HIGH":
        return 2
    if severity == "MEDIUM":
        return 3
    return 4  # LOW / default


def _make_recommendations(axis_id: str, severity: str) -> List[str]:
    """
    v0 recommendation templates based on axis_id patterns and severity.
    This is intentionally generic and non-prescriptive.
    """
    recs: List[str] = []

    # EPF-related paradox pattern
    if axis_id.startswith("paradox_pattern:epf_field_vs_policy_field"):
        recs.append(
            "Review EPF vs policy thresholds and align risk definitions "
            "for the affected segments."
        )
        recs.append(
            "Investigate scenarios where EPF shadow indicates high risk "
            "while gates remain PASS."
        )
        if severity in ("CRITICAL", "HIGH"):
            recs.append(
                "Consider introducing an EPF-informed review stage or "
                "separate approval path for high-tension runs."
            )
        return recs

    # Generic paradox_pattern axis
    if axis_id.startswith("paradox_pattern:"):
        pattern = axis_id.split("paradox_pattern:", 1)[1] or "unknown_pattern"
        recs.append(
            f"Analyse occurrences of paradox pattern '{pattern}' "
            "and identify common triggers."
        )
        recs.append(
            "Document the intended behaviour for this pattern and compare "
            "it with current gate / policy logic."
        )
        if severity in ("CRITICAL", "HIGH"):
            recs.append(
                "Propose a concrete mitigation or escalation workflow "
                "for this pattern (e.g. manual review, tighter thresholds)."
            )
        return recs

    # RDSI vs gate decision axis
    if axis_id == "rdsi_vs_gate_decision":
        recs.append(
            "Compare RDSI thresholds with current gate cutoffs and ensure "
            "they encode a consistent notion of 'stable enough'."
        )
        if severity in ("CRITICAL", "HIGH"):
            recs.append(
                "Investigate runs where RDSI indicates instability while "
                "gates remain PASS; consider adjusting thresholds or "
                "adding guardrail checks."
            )
        return recs

    # Default catch-all
    recs.append(
        "Review this paradox axis and clarify the intended relationship "
        "between A and notA in the system design."
    )
    if severity in ("CRITICAL", "HIGH"):
        recs.append(
            "Propose at least one mitigation experiment or policy change "
            "to reduce recurring high tension on this axis."
        )

    return recs


def build_paradox_resolution_v0(history: History) -> ResolutionPlan:
    """
    Build a resolution plan v0 from paradox_history_v0.json.
    """
    paradox_history = history.get("paradox_history") or {}
    axes = paradox_history.get("axes") or []
    num_runs = history.get("num_runs", 0)

    axis_plans: List[Dict[str, Any]] = []

    severity_counts = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
    }

    for ax in axes:
        if not isinstance(ax, dict):
            continue

        axis_id = ax.get("axis_id")
        if not axis_id:
            continue

        runs_seen = int(ax.get("runs_seen", 0))
        times_dominant = int(ax.get("times_dominant", 0))
        max_tension = _safe_float(ax.get("max_tension"))
        avg_tension = _safe_float(ax.get("avg_tension"))

        severity = _classify_severity(max_tension, avg_tension, runs_seen, times_dominant)
        priority = _priority_from_severity(severity)
        severity_counts[severity] += 1

        recs = _make_recommendations(axis_id, severity)

        axis_plans.append(
            {
                "axis_id": axis_id,
                "runs_seen": runs_seen,
                "times_dominant": times_dominant,
                "max_tension": max_tension,
                "avg_tension": avg_tension,
                "severity": severity,
                "priority": priority,
                "recommended_focus": recs,
            }
        )

    # Priority szerint rendezés (1 = legfontosabb)
    axis_plans.sort(key=lambda a: (a["priority"], -(a["max_tension"] or 0.0)))

    plan: ResolutionPlan = {
        "version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "num_runs_considered": num_runs,
        "summary": {
            "num_axes": len(axis_plans),
            "severity_counts": severity_counts,
        },
        "axes": axis_plans,
    }

    return plan


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paradox_resolution_v0.json from paradox_history_v0.json"
    )
    parser.add_argument(
        "--history",
        dest="history_path",
        default="paradox_history_v0.json",
        help="Path to paradox_history_v0.json (default: ./paradox_history_v0.json)",
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        default="paradox_resolution_v0.json",
        help="Output JSON path (default: ./paradox_resolution_v0.json)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    with open(args.history_path, "r", encoding="utf-8") as f:
        history: History = json.load(f)

    plan = build_paradox_resolution_v0(history)

    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print(
        f"[paradox_resolution_v0] built resolution plan for "
        f"{plan['summary']['num_axes']} axes into {args.out_path}"
    )


if __name__ == "__main__":
    main()
