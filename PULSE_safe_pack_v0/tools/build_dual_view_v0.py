#!/usr/bin/env python3
"""
PULSE Dual View v0 builder

Builds `dual_view_v0.json` as a shared human + agent interface on top of:
- stability_map.json (current ReleaseState)
- decision_trace.json (Decision Engine v0)
- optional stability_history.json (multi-run transitions)

The script is read-only: it does not modify any of the input artefacts.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone


def load_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def select_state(stability_map: dict, state_id: str | None = None) -> dict:
    states = stability_map.get("states") or []
    if not states:
        raise SystemExit("No states[] found in stability_map.json")

    if state_id is None:
        return states[0]

    for st in states:
        if str(st.get("id")) == state_id:
            return st

    raise SystemExit(f"State with id={state_id!r} not found in stability_map.json")


def find_last_transition_for_state(history: dict, state_id: str) -> dict | None:
    transitions = history.get("transitions") or []
    # We look for the last transition where `to == state_id`
    last = None
    for tr in transitions:
        if str(tr.get("to")) == state_id:
            last = tr
    return last


def build_human_view(
    state: dict,
    decision_trace: dict | None,
    last_transition: dict | None,
    risk_level: str,
) -> dict:
    instab = state.get("instability") or {}
    score = float(instab.get("score", 0.0) or 0.0)
    state_type = state.get("type") or "UNSTABLE"
    decision = state.get("decision") or "UNKNOWN"

    action = None
    summary = None
    if decision_trace:
        action = decision_trace.get("action")
        summary = decision_trace.get("summary")

    # Headline
    if action and risk_level:
        headline = f"{action} ({risk_level} risk, {state_type.lower()})."
    else:
        headline = f"{state_type} state with instability {score:.2f}."

    # Risk summary lines
    risk_summary: list[str] = []
    risk_summary.append(f"Overall instability: {score:.2f} ({risk_level}).")
    if action:
        risk_summary.append(f"Decision Engine action: {action}, PULSE decision: {decision}.")
    if summary:
        risk_summary.append(summary)

    # Paradox summary
    paradox = state.get("paradox") or {}
    if paradox.get("present"):
        patterns = paradox.get("patterns") or []
        if patterns:
            joined = ", ".join(patterns)
            paradox_summary = f"Paradox detected: {joined}."
        else:
            paradox_summary = "Paradox detected (no patterns listed)."
    else:
        paradox_summary = "No paradox detected."

    # Timeline highlights
    timeline_highlights: list[str] = []
    if last_transition:
        from_id = last_transition.get("from")
        to_id = last_transition.get("to")
        delta_inst = float(last_transition.get("delta_instability", 0.0) or 0.0)
        category = last_transition.get("category") or "NEUTRAL"
        timeline_highlights.append(
            f"{from_id} → {to_id}: {category} change (delta_instability = {delta_inst:+.2f})."
        )

    return {
        "headline": headline,
        "risk_summary": risk_summary,
        "paradox_summary": paradox_summary,
        "timeline_highlights": timeline_highlights,
    }


def build_agent_view(
    state: dict,
    decision_trace: dict | None,
    last_transition: dict | None,
    risk_level: str,
) -> dict:
    instab = state.get("instability") or {}
    score = float(instab.get("score", 0.0) or 0.0)

    components = {
        "safety": float(instab.get("safety_component", 0.0) or 0.0),
        "quality": float(instab.get("quality_component", 0.0) or 0.0),
        "rdsi": float(instab.get("rdsi_component", 0.0) or 0.0),
        "epf": float(instab.get("epf_component", 0.0) or 0.0),
    }

    paradox = state.get("paradox") or {}
    decision = state.get("decision") or "UNKNOWN"
    state_type = state.get("type") or "UNSTABLE"

    action = None
    if decision_trace:
        action = decision_trace.get("action") or None

    history_info = {"has_history": last_transition is not None}
    if last_transition:
        history_info["last_transition"] = {
            "from": last_transition.get("from"),
            "to": last_transition.get("to"),
            "delta_instability": float(
                last_transition.get("delta_instability", 0.0) or 0.0
            ),
            "category": last_transition.get("category"),
        }

    return {
        "action": action,
        "risk_level": risk_level,
        "instability": {
            "score": score,
            "components": components,
        },
        "paradox": {
            "present": bool(paradox.get("present")),
            "patterns": paradox.get("patterns") or [],
        },
        "decision": {
            "release_decision": decision,
            "stability_type": state_type,
        },
        "history": history_info,
    }


def derive_risk_level(decision_trace: dict | None, state: dict) -> str:
    if decision_trace and decision_trace.get("risk_level"):
        return str(decision_trace.get("risk_level"))

    # Fallback: derive from instability score
    instab = state.get("instability") or {}
    score = float(instab.get("score", 0.0) or 0.0)
    if score < 0.30:
        return "LOW"
    if score < 0.60:
        return "MEDIUM"
    return "HIGH"


def main():
    parser = argparse.ArgumentParser(description="Build PULSE Dual View v0 artefact.")
    parser.add_argument(
        "--stability-map",
        type=Path,
        default=Path("PULSE_safe_pack_v0/artifacts/stability_map.json"),
        help="Path to stability_map.json",
    )
    parser.add_argument(
        "--decision-trace",
        type=Path,
        default=Path("PULSE_safe_pack_v0/artifacts/decision_trace.json"),
        help="Path to decision_trace.json",
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=Path("PULSE_safe_pack_v0/artifacts/stability_history.json"),
        help="Path to stability_history.json (optional)",
    )
    parser.add_argument(
        "--state-id",
        type=str,
        default=None,
        help="Optional state id to focus on (defaults to first state)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("PULSE_safe_pack_v0/artifacts/dual_view_v0.json"),
        help="Output path for dual_view_v0.json",
    )

    args = parser.parse_args()

    stability_map = load_json(args.stability_map)
    if stability_map is None:
        raise SystemExit(f"Cannot load stability map from: {args.stability_map}")

    decision_trace = load_json(args.decision_trace)
    history = load_json(args.history) or stability_map  # fallback: use same file

    state = select_state(stability_map, args.state_id)
    state_id = state.get("id")

    last_transition = None
    if history is not None and state_id is not None:
        last_transition = find_last_transition_for_state(history, str(state_id))

    risk_level = derive_risk_level(decision_trace, state)

    human_view = build_human_view(state, decision_trace, last_transition, risk_level)
    agent_view = build_agent_view(state, decision_trace, last_transition, risk_level)

    dual_view = {
        "version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "state_id": state_id,
        "human_view": human_view,
        "agent_view": agent_view,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(dual_view, f, indent=2, ensure_ascii=False)

    print(human_view["headline"])


if __name__ == "__main__":
    main()
