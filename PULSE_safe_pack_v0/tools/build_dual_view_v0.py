#!/usr/bin/env python3

"""
PULSE Dual View v0 builder

This tool builds a minimal dual_view_v0.json artefact from:
- a Stability Map (`stability_map.json`-szerű),
- a Decision Engine output (`decision_trace.json`-szerű).

It is intentionally simple and designed to match:
- `PULSE_dual_view_v0.md`
- `docs/examples/topology_demo_v0/dual_view_v0.run_002.demo.json`.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_state(stability_map: Dict[str, Any], state_id: str) -> Dict[str, Any]:
    for st in stability_map.get("states", []):
        if st.get("id") == state_id:
            return st
    raise ValueError(f"State with id={state_id!r} not found in stability map.")


def find_last_transition(
    stability_map: Dict[str, Any], state_id: str
) -> Optional[Dict[str, Any]]:
    transitions = stability_map.get("transitions", [])
    # Assume transitions are ordered; take the last where `to` == state_id.
    candidates = [t for t in transitions if t.get("to") == state_id]
    if not candidates:
        return None
    return candidates[-1]


def build_dual_view(
    stability_map: Dict[str, Any],
    decision_trace: Dict[str, Any],
    state_id: Optional[str] = None,
) -> Dict[str, Any]:
    # Determine state_id: explicit arg → from decision_trace
    if state_id is None:
        state_id = decision_trace.get("state_id")
    if not state_id:
        raise ValueError("state_id not provided and not found in decision trace.")

    state = find_state(stability_map, state_id)
    last_transition = find_last_transition(stability_map, state_id)

    action = decision_trace.get("action", "UNKNOWN")
    risk_level = decision_trace.get("risk_level", "MEDIUM")
    details = decision_trace.get("details", {})

    release_decision = details.get("release_decision", "UNKNOWN")
    stability_type = details.get("stability_type", "UNKNOWN")

    instability_score = details.get("instability_score")
    instability_components = details.get("instability_components", {})
    paradox_present = bool(details.get("paradox_present", False))

    # Human view
    headline = decision_trace.get(
        "summary",
        f"{action} decision with {risk_level} risk for state {state_id}.",
    )

    risk_summary = [
        f"Action: {action}, risk level: {risk_level}.",
        f"Release decision: {release_decision}, stability type: {stability_type}.",
    ]

    if instability_score is not None:
        risk_summary.append(f"Overall instability: {instability_score}.")

    paradox_summary = (
        "Paradox detected." if paradox_present else "No paradox detected."
    )

    timeline_highlights = []
    if last_transition is not None:
        from_id = last_transition.get("from")
        category = last_transition.get("category", "NEUTRAL")
        di = last_transition.get("delta_instability")
        highlight = f"{from_id} → {state_id}: {category}"
        if di is not None:
            highlight += f" (delta_instability = {di})"
        timeline_highlights.append(highlight)

    # Agent view
    agent_instability = {
        "score": instability_score,
        "components": instability_components,
    }

    state_paradox = state.get("paradox", {}) or {}
    paradox_patterns = state_paradox.get("patterns", [])

    agent_paradox = {
        "present": paradox_present,
        "patterns": paradox_patterns,
    }

    agent_decision = {
        "release_decision": release_decision,
        "stability_type": stability_type,
    }

    history: Dict[str, Any] = {
        "has_history": bool(stability_map.get("transitions")),
        "last_transition": None,
    }
    if last_transition is not None:
        history["last_transition"] = {
            "from": last_transition.get("from"),
            "to": last_transition.get("to"),
            "delta_instability": last_transition.get("delta_instability"),
            "category": last_transition.get("category"),
        }

    dual_view = {
        "version": "0.1",
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "state_id": state_id,
        "human_view": {
            "headline": headline,
            "risk_summary": risk_summary,
            "paradox_summary": paradox_summary,
            "timeline_highlights": timeline_highlights,
        },
        "agent_view": {
            "action": action,
            "risk_level": risk_level,
            "instability": agent_instability,
            "paradox": agent_paradox,
            "decision": agent_decision,
            "history": history,
        },
    }

    return dual_view


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a PULSE Dual View v0 artefact "
        "from a Stability Map and Decision Trace."
    )
    parser.add_argument(
        "--stability-map",
        required=True,
        type=Path,
        help="Path to stability_map.json (or compatible) input.",
    )
    parser.add_argument(
        "--decision-trace",
        required=True,
        type=Path,
        help="Path to decision_trace.json input.",
    )
    parser.add_argument(
        "--state-id",
        required=False,
        help="Optional state id to use; defaults to decision_trace.state_id.",
    )
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output path for dual_view_v0.json.",
    )

    args = parser.parse_args()

    stability_map = load_json(args.stability_map)
    decision_trace = load_json(args.decision_trace)

    dual_view = build_dual_view(
        stability_map=stability_map,
        decision_trace=decision_trace,
        state_id=args.state_id,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(dual_view, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
