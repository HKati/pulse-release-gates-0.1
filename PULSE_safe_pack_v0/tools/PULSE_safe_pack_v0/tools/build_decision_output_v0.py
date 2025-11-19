#!/usr/bin/env python
"""
build_decision_output_v0.py

Shadow-only Decision Engine v0 output builder on top of stability_map.json.

Input:
    - stability_map.json (Topology v0), already augmented with:
        - ReleaseState.paradox_field_v0
        - ReleaseState.epf_field_v0
      via build_paradox_epf_fields_v0.py

Output:
    - decision_output_v0.json (by default), with:
        - run_id, decision
        - release_state (the selected ReleaseState, typically the latest)
        - paradox_field_v0, epf_field_v0 (copied from the state)
        - decision_trace[] with a paradox_stamp
        - dual_view with a paradox panel

This tool does NOT modify any gate logic.
"""

import argparse
import json
from typing import Any, Dict, List, Optional


StabilityMap = Dict[str, Any]
State = Dict[str, Any]
DecisionOutput = Dict[str, Any]
TraceStep = Dict[str, Any]


def _select_state(stability_map: StabilityMap) -> Optional[State]:
    """
    Select the primary ReleaseState to represent in the Decision Engine output.

    v0: pick the last state in stability_map["states"] (assumed "latest run").
    """
    states = stability_map.get("states")
    if not isinstance(states, list) or not states:
        return None
    last_state = states[-1]
    return last_state if isinstance(last_state, dict) else None


def _get_top_paradox_atom(paradox_field_v0: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return the paradox atom with the highest tension_score, if any."""
    if not paradox_field_v0:
        return None
    atoms = paradox_field_v0.get("atoms") or []
    if not isinstance(atoms, list) or not atoms:
        return None
    top = max(atoms, key=lambda a: a.get("tension_score", 0.0))
    return top if isinstance(top, dict) else None


def _build_paradox_stamp(paradox_field_v0: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Build a minimal paradox_stamp from the strongest paradox atom:

        {
            "axis_id": ...,
            "direction": ...,
            "tension_score": ...,
            "zone": ...
        }
    """
    top_atom = _get_top_paradox_atom(paradox_field_v0)
    if top_atom is None:
        return None

    return {
        "axis_id": top_atom.get("axis_id"),
        "direction": top_atom.get("direction"),
        "tension_score": top_atom.get("tension_score"),
        "zone": top_atom.get("zone"),
    }


def _build_decision_trace_v0(state: State, paradox_field_v0: Optional[Dict[str, Any]]) -> List[TraceStep]:
    """
    Minimal decision_trace v0:

    - single step: the final gate decision, with a paradox_stamp.
    """
    trace: List[TraceStep] = []

    gate_summary = state.get("gate_summary") or {}
    instability = state.get("instability") or {}
    epf = state.get("epf") or {}

    paradox_stamp = _build_paradox_stamp(paradox_field_v0)

    step: TraceStep = {
        "step_id": "final_gate_decision",
        "kind": "gate_output_v0",
        "input": {
            "rdsi": state.get("rdsi"),
            "instability_score": instability.get("score"),
            "instability_components": {
                "safety_component": instability.get("safety_component"),
                "quality_component": instability.get("quality_component"),
                "rdsi_component": instability.get("rdsi_component"),
                "epf_component": instability.get("epf_component"),
            },
            "gate_summary": gate_summary,
            "epf": {
                "available": epf.get("available"),
                "L": epf.get("L"),
                "shadow_pass": epf.get("shadow_pass"),
            },
        },
        "output": {
            "decision": state.get("decision"),
            "type": state.get("type"),
            "tags": state.get("tags") or [],
        },
    }

    if paradox_stamp is not None:
        step["paradox_stamp"] = paradox_stamp

    trace.append(step)
    return trace


def _build_dual_view_v0(state: State,
                        paradox_field_v0: Optional[Dict[str, Any]],
                        epf_field_v0: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Dual View v0 structure with a paradox panel (shadow-only)."""
    instability = state.get("instability") or {}
    epf = state.get("epf") or {}

    summary_panel = {
        "decision": state.get("decision"),
        "type": state.get("type"),
        "rdsi": state.get("rdsi"),
        "instability_score": instability.get("score"),
        "epf_available": epf.get("available"),
    }

    paradox_panel = {
        "paradox_summary": (paradox_field_v0 or {}).get("summary"),
        "epf_field": epf_field_v0,
        "note": (
            "Paradoxon- és EPF-mező v0 – shadow-only réteg; "
            "a release gate döntési fáját nem módosítja."
        ),
    }

    return {
        "summary_panel_v0": summary_panel,
        "paradox_panel_v0": paradox_panel,
    }


def build_decision_output_v0(stability_map: StabilityMap) -> DecisionOutput:
    """
    Build the Decision Engine v0 output structure from stability_map.json.

    - selects a primary ReleaseState (latest)
    - pulls paradox_field_v0 and epf_field_v0 from that state
    - builds a minimal decision_trace with paradox_stamp
    - builds a dual_view with a paradox panel
    """
    state = _select_state(stability_map)
    if state is None:
        raise ValueError("stability_map.states is missing or empty; cannot build decision_output_v0")

    paradox_field_v0 = state.get("paradox_field_v0")
    epf_field_v0 = state.get("epf_field_v0")

    decision_trace = _build_decision_trace_v0(state, paradox_field_v0)
    dual_view = _build_dual_view_v0(state, paradox_field_v0, epf_field_v0)

    output: DecisionOutput = {
        "version": "0.1",
        "generated_at": stability_map.get("generated_at"),
        "run_id": state.get("id"),
        "decision": state.get("decision"),
        "release_state": state,
        "paradox_field_v0": paradox_field_v0,
        "epf_field_v0": epf_field_v0,
        "decision_trace": decision_trace,
        "dual_view": dual_view,
    }

    return output


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Decision Engine v0 output (shadow-only) from stability_map.json"
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
        default="decision_output_v0.json",
        help="Output JSON path (default: ./decision_output_v0.json)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    with open(args.map_path, "r", encoding="utf-8") as f:
        stability_map: StabilityMap = json.load(f)

    decision_output = build_decision_output_v0(stability_map)

    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump(decision_output, f, indent=2, ensure_ascii=False)

    print(f"[decision_output_v0] wrote {args.out_path}")


if __name__ == "__main__":
    main()
