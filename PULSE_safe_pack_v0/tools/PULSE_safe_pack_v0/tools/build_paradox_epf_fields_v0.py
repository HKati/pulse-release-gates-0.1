#!/usr/bin/env python
"""
build_paradox_epf_fields_v0.py

Shadow-only augmentation tool for stability_map.json:

- For each ReleaseState in `states[]`, attach:
  - `paradox_field_v0`: paradox atoms + summary (per state)
  - `epf_field_v0`: EPF physical field (phi/theta/energy + anchors) per state

This does NOT change gate logic or existing fields (`rdsi`, `epf`, `paradox`, etc.).
It only adds new fields that are now allowed by PULSE_stability_map_v0.schema.json.
"""

import argparse
import json
from typing import Any, Dict, List, Optional


State = Dict[str, Any]
StabilityMap = Dict[str, Any]


def _zone_from_tension(tension: float) -> str:
    """Map [0,1] tension score to green/yellow/red."""
    if tension >= 0.66:
        return "red"
    if tension >= 0.33:
        return "yellow"
    return "green"


def _decision_score(decision: Optional[str]) -> Optional[float]:
    """
    Rough scalar for gate decision, used only to build a paradox tension signal.

    FAIL        → 0.0
    STAGE-PASS  → 0.6
    PROD-PASS   → 1.0
    UNKNOWN     → 0.5
    """
    if decision is None:
        return None
    if decision == "FAIL":
        return 0.0
    if decision == "STAGE-PASS":
        return 0.6
    if decision == "PROD-PASS":
        return 1.0
    if decision == "UNKNOWN":
        return 0.5
    return None


def _clamp_01(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _build_paradox_atoms_for_state(state: State) -> List[Dict[str, Any]]:
    """
    Build paradox atoms for a single ReleaseState.

    v0: két forrásból dolgozik:
    - RDSI vs gate decision feszültség (axis: rdsi_vs_gate_decision)
    - explicit paradox blokkból (axis: paradox_pattern:<pattern>)
    """
    atoms: List[Dict[str, Any]] = []

    state_id = state.get("id")
    decision = state.get("decision")
    rdsi = state.get("rdsi")

    # --- 1) RDSI vs gate decision tengely ----------------------------

    gate_score = _decision_score(decision)
    rdsi_norm = _clamp_01(rdsi)

    if gate_score is not None and rdsi_norm is not None:
        tension = abs(gate_score - rdsi_norm)
        zone = _zone_from_tension(tension)

        atoms.append(
            {
                # axis: gate decision vs rdsi
                "axis_id": "rdsi_vs_gate_decision",
                "A": "gate_decision_consistent_with_rdsi",
                "notA": "gate_decision_in_tension_with_rdsi",
                "direction": "towards_A" if tension < 0.2 else "towards_notA",
                "tension_score": float(tension),
                "zone": zone,
                "context": {
                    "run_id": state_id,
                    "scope": "stability_map",
                    "segment": "rdsi_vs_gate_decision",
                },
                "anchors": [
                    {
                        "topology_node": "decision_engine/gate",
                        "role": "decision_point",
                    }
                ],
            }
        )

    # --- 2) Paradox blokk → paradox_pattern tengelyek ----------------

    paradox = state.get("paradox") or {}
    if paradox.get("present"):
        details = paradox.get("details") or []
        resolution = paradox.get("resolution") or {}
        severity = resolution.get("severity")

        base_tension = {
            "LOW": 0.3,
            "MEDIUM": 0.6,
            "HIGH": 0.9,
        }.get(severity, 0.5)

        for detail in details:
            pattern = detail.get("pattern") or "unknown_pattern"
            reason = detail.get("reason") or ""

            axis_id = f"paradox_pattern:{pattern}"

            atoms.append(
                {
                    "axis_id": axis_id,
                    "A": "system_behaviour_consistent",
                    "notA": f"paradox_pattern_active:{pattern}",
                    "direction": "towards_stability"
                    if severity == "LOW"
                    else "unresolved",
                    "tension_score": float(base_tension),
                    "zone": _zone_from_tension(base_tension),
                    "context": {
                        "run_id": state_id,
                        "scope": "stability_map",
                        "segment": f"paradox:{pattern}",
                        "reason": reason,
                    },
                    "anchors": [
                        {
                            "topology_node": "stability_map/state",
                            "role": "paradox_flag",
                        }
                    ],
                }
            )

    return atoms


def _summarise_paradox_field(atoms: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not atoms:
        return {
            "max_tension": 0.0,
            "num_atoms": 0,
            "num_red_zones": 0,
            "num_yellow_zones": 0,
            "dominant_axes": [],
        }

    max_tension = max(a.get("tension_score", 0.0) for a in atoms)
    num_red = sum(1 for a in atoms if a.get("zone") == "red")
    num_yellow = sum(1 for a in atoms if a.get("zone") == "yellow")

    axes = {}
    for a in atoms:
        axis = a.get("axis_id")
        if axis is None:
            continue
        t = a.get("tension_score", 0.0)
        axes[axis] = max(axes.get(axis, 0.0), t)

    dominant_axes = sorted(
        axes.keys(), key=lambda ax: axes[ax], reverse=True
    )

    return {
        "max_tension": max_tension,
        "num_atoms": len(atoms),
        "num_red_zones": num_red,
        "num_yellow_zones": num_yellow,
        "dominant_axes": dominant_axes,
    }


def _build_epf_field_for_state(state: State) -> Optional[Dict[str, Any]]:
    """
    EPF mező v0 egy ReleaseState-re.

    Forrás: a meglévő `epf` blokk:
    - epf.available (bool)
    - epf.L (number | null)
    - epf.shadow_pass (bool | null)
    """
    epf = state.get("epf") or {}
    if not epf.get("available"):
        return None

    L = epf.get("L")
    shadow_pass = epf.get("shadow_pass")

    # phi_potential: v0-ban egyszerűen L-t visszük át (ha van)
    phi_potential = None
    try:
        if L is not None:
            phi_potential = float(L)
    except (TypeError, ValueError):
        phi_potential = None

    # theta_distortion: 0 ha shadow_pass True, 1 ha False, különben None
    if shadow_pass is True:
        theta_distortion: Optional[float] = 0.0
    elif shadow_pass is False:
        theta_distortion = 1.0
    else:
        theta_distortion = None

    energy_delta: Optional[float] = None  # v0: nincs külön energia-jel

    anchors: List[Dict[str, Any]] = [
        {
            "topology_node": "decision_engine/gate",
            "potential": phi_potential,
            "deflection": theta_distortion,
        }
    ]

    return {
        "phi_potential": phi_potential,
        "theta_distortion": theta_distortion,
        "energy_delta": energy_delta,
        "anchors": anchors,
        "linked_paradoxes": [],  # későbbi verziók köthetik a paradox_atomid-khez
    }


def attach_paradox_epf_fields_v0(stability_map: StabilityMap) -> StabilityMap:
    """
    Attach paradox_field_v0 and epf_field_v0 to each ReleaseState in the map.

    A `stability_map` séma szerint:
    - root: { version, generated_at, states[], transitions[] }
    - states[]: ReleaseState
    """
    states = stability_map.get("states")
    if not isinstance(states, list):
        return stability_map

    for state in states:
        if not isinstance(state, dict):
            continue

        # paradox_field_v0
        atoms = _build_paradox_atoms_for_state(state)
        state["paradox_field_v0"] = {
            "atoms": atoms,
            "summary": _summarise_paradox_field(atoms),
        }

        # epf_field_v0
        epf_field = _build_epf_field_for_state(state)
        if epf_field is not None:
            state["epf_field_v0"] = epf_field

    return stability_map


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Attach paradox_field_v0 and epf_field_v0 to stability_map.json"
    )
    parser.add_argument(
        "--map",
        dest="map_path",
        default="stability_map.json",
        help="Path to stability_map.json (default: stability_map.json in repo root)",
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        default=None,
        help="Output path (default: overwrite input file in-place).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    in_path = args.map_path
    out_path = args.out_path or in_path

    with open(in_path, "r", encoding="utf-8") as f:
        stability_map: StabilityMap = json.load(f)

    stability_map = attach_paradox_epf_fields_v0(stability_map)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stability_map, f, indent=2, ensure_ascii=False)

    print(f"[paradox_epf_v0] updated {out_path}")


if __name__ == "__main__":
    main()
