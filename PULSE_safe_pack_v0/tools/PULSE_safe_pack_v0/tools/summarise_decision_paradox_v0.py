#!/usr/bin/env python
"""
summarise_decision_paradox_v0.py

Mini "dashboard JSON" builder for Decision Engine v0 + paradox/EPF field.

Input:
    - decision_output_v0.json
      (produced by build_decision_output_v0.py)

Output:
    - decision_paradox_summary_v0.json (by default), with:
        - run_id, decision, type
        - stability snapshot (rdsi, instability_score)
        - paradox overview (max tension, dominant axes, per-axis stats)
        - EPF overview (phi/theta/energy)
"""

import argparse
import json
from typing import Any, Dict, List, Optional


DecisionOutput = Dict[str, Any]
Summary = Dict[str, Any]


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def _summarise_paradox_axes(paradox_field_v0: Dict[str, Any]) -> Dict[str, Any]:
    atoms = paradox_field_v0.get("atoms") or []
    if not isinstance(atoms, list):
        atoms = []

    summary = paradox_field_v0.get("summary") or {}
    max_tension = _safe_float(summary.get("max_tension")) or 0.0
    dominant_axes = summary.get("dominant_axes") or []

    # per-axis aggregáció
    axes: Dict[str, Dict[str, Any]] = {}
    for atom in atoms:
        if not isinstance(atom, dict):
            continue
        axis = atom.get("axis_id")
        if not axis:
            continue
        t = _safe_float(atom.get("tension_score")) or 0.0
        zone = atom.get("zone") or "green"

        ax = axes.setdefault(
            axis,
            {
                "axis_id": axis,
                "max_tension": 0.0,
                "num_atoms": 0,
                "num_red": 0,
                "num_yellow": 0,
                "num_green": 0,
            },
        )

        ax["num_atoms"] += 1
        if t > ax["max_tension"]:
            ax["max_tension"] = t

        if zone == "red":
            ax["num_red"] += 1
        elif zone == "yellow":
            ax["num_yellow"] += 1
        else:
            ax["num_green"] += 1

    # listává alakítás, max_tension szerint rendezve
    axes_list = sorted(
        axes.values(), key=lambda a: a["max_tension"], reverse=True
    )

    return {
        "max_tension": max_tension,
        "dominant_axes": dominant_axes,
        "axes": axes_list,
    }


def build_decision_paradox_summary_v0(
    decision_output: DecisionOutput,
) -> Summary:
    """Build a compact dashboard-style summary from decision_output_v0."""
    run_id = decision_output.get("run_id")
    decision = decision_output.get("decision")

    release_state = decision_output.get("release_state") or {}
    instability = release_state.get("instability") or {}

    paradox_field_v0 = decision_output.get("paradox_field_v0") or {}
    epf_field_v0 = decision_output.get("epf_field_v0") or {}

    rdsi = _safe_float(release_state.get("rdsi"))
    instability_score = _safe_float(instability.get("score"))

    paradox_overview = _summarise_paradox_axes(paradox_field_v0)

    epf_overview = {
        "phi_potential": _safe_float(epf_field_v0.get("phi_potential")),
        "theta_distortion": _safe_float(epf_field_v0.get("theta_distortion")),
        "energy_delta": _safe_float(epf_field_v0.get("energy_delta")),
    }

    return {
        "version": "0.1",
        "run_id": run_id,
        "decision": decision,
        "type": release_state.get("type"),
        "stability": {
            "rdsi": rdsi,
            "instability_score": instability_score,
        },
        "paradox_overview": paradox_overview,
        "epf_overview": epf_overview,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarise decision_output_v0.json into a dashboard-style JSON"
    )
    parser.add_argument(
        "--decision",
        dest="decision_path",
        default="decision_output_v0.json",
        help="Path to decision_output_v0.json (default: ./decision_output_v0.json)",
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        default="decision_paradox_summary_v0.json",
        help="Output JSON path (default: ./decision_paradox_summary_v0.json)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    with open(args.decision_path, "r", encoding="utf-8") as f:
        decision_output: DecisionOutput = json.load(f)

    summary = build_decision_paradox_summary_v0(decision_output)

    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"[decision_paradox_summary_v0] wrote {args.out_path}")


if __name__ == "__main__":
    main()
