#!/usr/bin/env python
"""
build_topology_dashboard_v0.py

Build a topology dashboard v0 JSON on top of stability_map.json.

Input:
    - stability_map.json (Topology v0), with:
        - states[]: ReleaseState (including paradox_field_v0 / epf_field_v0 if present)
        - transitions[]: ReleaseTransition

Output:
    - topology_dashboard_v0.json (by default), with:
        - states[]: one row per ReleaseState (decision + stability + paradox + EPF snapshot)
        - transitions[]: simplified transition info for dashboards

This tool does NOT touch any gate logic; it is a derived, dashboard-oriented view.
"""

import argparse
import json
from typing import Any, Dict, List, Optional


StabilityMap = Dict[str, Any]
Dashboard = Dict[str, Any]


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


def build_topology_dashboard_v0(stability_map: StabilityMap) -> Dashboard:
    """Build a dashboard-style view across all ReleaseStates and transitions."""
    states_in = stability_map.get("states") or []
    transitions_in = stability_map.get("transitions") or []

    states_out: List[Dict[str, Any]] = []

    for state in states_in:
        if not isinstance(state, dict):
            continue

        state_id = state.get("id")
        label = state.get("label")
        decision = state.get("decision")
        type_ = state.get("type")

        rdsi = _safe_float(state.get("rdsi"))
        instability = state.get("instability") or {}
        instability_score = _safe_float(instability.get("score"))

        paradox_field = state.get("paradox_field_v0") or {}
        paradox_summary = paradox_field.get("summary") or {}
        paradox_max_tension = _safe_float(paradox_summary.get("max_tension"))
        paradox_zone = _zone_from_tension(paradox_max_tension)
        paradox_dominant_axes = paradox_summary.get("dominant_axes") or []

        epf_field = state.get("epf_field_v0") or {}
        epf_phi = _safe_float(epf_field.get("phi_potential"))
        epf_theta = _safe_float(epf_field.get("theta_distortion"))
        epf_energy = _safe_float(epf_field.get("energy_delta"))

        headline_parts = [
            f"run={state_id}",
            f"decision={decision}",
            f"type={type_}",
            f"instability={instability_score}",
            f"paradox_zone={paradox_zone}",
            f"paradox_tension={paradox_max_tension}",
            f"epf_phi={epf_phi}",
            f"epf_theta={epf_theta}",
        ]
        headline = " | ".join(str(p) for p in headline_parts)

        states_out.append(
            {
                "id": state_id,
                "label": label,
                "decision": decision,
                "type": type_,
                "rdsi": rdsi,
                "instability_score": instability_score,
                "paradox_zone": paradox_zone,
                "paradox_max_tension": paradox_max_tension,
                "paradox_dominant_axes": paradox_dominant_axes,
                "epf_phi_potential": epf_phi,
                "epf_theta_distortion": epf_theta,
                "epf_energy_delta": epf_energy,
                "headline": headline,
            }
        )

    transitions_out: List[Dict[str, Any]] = []
    for tr in transitions_in:
        if not isinstance(tr, dict):
            continue

        transitions_out.append(
            {
                "from": tr.get("from"),
                "to": tr.get("to"),
                "label": tr.get("label"),
                "delta_instability": _safe_float(tr.get("delta_instability")),
                "delta_rdsi": _safe_float(tr.get("delta_rdsi")),
                "delta_epf_L": _safe_float(tr.get("delta_epf_L")),
                "category": tr.get("category"),
                "tags": tr.get("tags") or [],
            }
        )

    return {
        "version": "0.1",
        "generated_at": stability_map.get("generated_at"),
        "num_states": len(states_out),
        "states": states_out,
        "transitions": transitions_out,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build topology_dashboard_v0.json from stability_map.json"
    )
    parser.add_argument(
        "--map",
        dest="map_path",
        default="stability_map.json",
        help="Path to stability_map.json (default: ./stability_map.json)",
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        default="topology_dashboard_v0.json",
        help="Output JSON path (default: ./topology_dashboard_v0.json)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    with open(args.map_path, "r", encoding="utf-8") as f:
        stability_map: StabilityMap = json.load(f)

    dashboard = build_topology_dashboard_v0(stability_map)

    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)

    print(
        f"[topology_dashboard_v0] built dashboard for "
        f"{dashboard.get('num_states', 0)} states into {args.out_path}"
    )


if __name__ == "__main__":
    main()
