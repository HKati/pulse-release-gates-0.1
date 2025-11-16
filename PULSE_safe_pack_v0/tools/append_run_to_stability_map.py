#!/usr/bin/env python3
"""
PULSE Topology Transitions v0 — append run to Stability Map

This tool:

- reads an existing stability_map.json (if present)
- builds a new ReleaseState from status.json + optional status_epf.json
  using the same logic as build_stability_map.py
- appends the new state to `states[]`
- creates a ReleaseTransition from the previous state to the new one
  with delta-instability metrics and a coarse category
- writes the updated stability_map.json

If no existing Stability Map is found, this tool behaves like a simple
builder and creates a map with a single state and no transitions.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

# We reuse the core logic from build_stability_map.py
from .build_stability_map import (
    load_json,
    compute_instability,
    classify_type,
    detect_paradox,
)


def build_state_from_status(status_path: Path, status_epf_path: Path | None) -> dict:
    status = load_json(status_path)
    if status is None:
        raise SystemExit(f"Cannot find status.json at: {status_path}")

    status_epf = load_json(status_epf_path) if status_epf_path is not None else None

    gates, instab_components, epf_meta, rdsi = compute_instability(status, status_epf)

    decision = (
        status.get("release_level")
        or status.get("decision", {}).get("level")
        or status.get("decision", {}).get("release_level")
        or "UNKNOWN"
    )

    run_id = (
        status.get("run_id")
        or status.get("meta", {}).get("run_id")
        or status.get("meta", {}).get("commit")
        or "current_run"
    )

    state_type = classify_type(
        decision,
        instab_components["score"],
        gates["safety_failed"],
        gates["quality_failed"],
    )

    state: dict = {
        "id": run_id,
        "label": f"Run {run_id}",
        "commit": status.get("meta", {}).get("commit"),
        "pack": "PULSE_safe_pack_v0",
        "decision": decision,
        "gate_summary": {
            "safety_total": gates["safety_total"],
            "safety_failed": gates["safety_failed"],
            "quality_total": gates["quality_total"],
            "quality_failed": gates["quality_failed"],
        },
        "rdsi": rdsi,
        "rdsi_delta": status.get("metrics", {}).get("rdsi_delta"),
        "epf": epf_meta,
        "instability": instab_components,
        "type": state_type,
        "tags": status.get("tags", []),
    }

    # Paradox detection v0 integration
    paradox_info = detect_paradox(state)
    state["paradox"] = paradox_info
    if paradox_info.get("present") and state["type"] != "COLLAPSE":
        state["type"] = "PARADOX"

    return state


def compute_transition_category(delta_instability: float) -> str:
    if delta_instability < -0.05:
        return "STABILISING"
    if delta_instability > 0.05:
        return "DESTABILISING"
    return "NEUTRAL"


def build_transition(
    prev_state: dict,
    new_state: dict,
    label: str | None = None,
    change_type: list[str] | None = None,
    notes: str | None = None,
) -> dict:
    prev_id = prev_state.get("id")
    new_id = new_state.get("id")

    prev_score = float(prev_state.get("instability", {}).get("score", 0.0) or 0.0)
    new_score = float(new_state.get("instability", {}).get("score", 0.0) or 0.0)
    delta_instability = new_score - prev_score

    prev_rdsi = prev_state.get("rdsi")
    new_rdsi = new_state.get("rdsi")
    delta_rdsi = None
    if prev_rdsi is not None and new_rdsi is not None:
        delta_rdsi = new_rdsi - prev_rdsi

    prev_epf_L = (prev_state.get("epf") or {}).get("L")
    new_epf_L = (new_state.get("epf") or {}).get("L")
    delta_epf_L = None
    if prev_epf_L is not None and new_epf_L is not None:
        delta_epf_L = new_epf_L - prev_epf_L

    category = compute_transition_category(delta_instability)

    if not label:
        label = f"{prev_id} → {new_id}"
    if change_type is None:
        change_type = ["unspecified"]
    change = {
        "type": change_type,
        "notes": notes or "",
    }

    transition: dict = {
        "from": prev_id,
        "to": new_id,
        "label": label,
        "change": change,
        "delta_instability": delta_instability,
        "category": category,
    }

    if delta_rdsi is not None:
        transition["delta_rdsi"] = delta_rdsi
    if delta_epf_L is not None:
        transition["delta_epf_L"] = delta_epf_L

    return transition


def main():
    parser = argparse.ArgumentParser(
        description="Append a run to stability_map.json and create a transition."
    )
    parser.add_argument(
        "--status",
        type=Path,
        default=Path("PULSE_safe_pack_v0/artifacts/status.json"),
        help="Path to status.json for the new run",
    )
    parser.add_argument(
        "--status-epf",
        type=Path,
        default=Path("PULSE_safe_pack_v0/artifacts/status_epf.json"),
        help="Path to status_epf.json for the new run (optional)",
    )
    parser.add_argument(
        "--map",
        type=Path,
        default=Path("PULSE_safe_pack_v0/artifacts/stability_map.json"),
        help="Path to stability_map.json (existing or to be created)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path for updated stability_map.json (defaults to --map)",
    )
    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Optional human-readable label for the transition",
    )
    parser.add_argument(
        "--change-type",
        type=str,
        default=None,
        help="Comma-separated list of change types (e.g. data,training,policy)",
    )
    parser.add_argument(
        "--notes",
        type=str,
        default=None,
        help="Optional free-text description of what changed between runs",
    )

    args = parser.parse_args()
    out_path = args.out or args.map

    # Load existing Stability Map if present
    if args.map.exists():
        with args.map.open("r", encoding="utf-8") as f:
            stability_map = json.load(f)
    else:
        stability_map = {
            "version": "0.1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "states": [],
            "transitions": [],
        }

    states = stability_map.get("states") or []
    transitions = stability_map.get("transitions") or []

    new_state = build_state_from_status(args.status, args.status_epf)

    if states:
        prev_state = states[-1]
        change_type = (
            [t.strip() for t in args.change_type.split(",")]
            if args.change_type
            else None
        )
        transition = build_transition(
            prev_state=prev_state,
            new_state=new_state,
            label=args.label,
            change_type=change_type,
            notes=args.notes,
        )
        transitions.append(transition)

    states.append(new_state)

    stability_map["states"] = states
    stability_map["transitions"] = transitions
    stability_map["generated_at"] = datetime.now(timezone.utc).isoformat()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(stability_map, f, indent=2, ensure_ascii=False)

    print(f"Updated Stability Map written to: {out_path}")


if __name__ == "__main__":
    main()
