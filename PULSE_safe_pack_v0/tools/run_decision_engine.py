#!/usr/bin/env python3
"""
PULSE Decision Engine v0

Reads a Stability Map artefact (stability_map.json) and produces a
decision_trace.json with an advisory action and explanation for the
selected ReleaseState.

This script is intentionally conservative and read-only:
it never modifies existing PULSE decisions or artefacts.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def select_state(stability_map: dict, state_id: str | None = None) -> dict:
    states = stability_map.get("states") or []
    if not states:
        raise SystemExit("No states found in stability_map.json")

    if state_id is None:
        # v0: just take the first state
        return states[0]

    for st in states:
        if str(st.get("id")) == state_id:
            return st

    raise SystemExit(f"State with id={state_id!r} not found in stability_map.json")


def compute_risk_level(score: float) -> str:
    if score < 0.30:
        return "LOW"
    if score < 0.60:
        return "MEDIUM"
    return "HIGH"


def decide_action(decision: str, state_type: str, score: float) -> str:
    d = (decision or "").upper()
    t = (state_type or "").upper()

    # 1. Hard fail from gates
    if d == "FAIL":
        return "BLOCK"

    # 2. Collapse or paradox regions
    if t == "COLLAPSE":
        return "BLOCK"
    if t == "PARADOX":
        return "REVIEW"

    # 3. Staging decisions
    if d == "STAGE-PASS":
        if score < 0.60:
            return "STAGE_ONLY"
        return "REVIEW"

    # 4. Production decisions
    if d == "PROD-PASS":
        if score < 0.30:
            return "PROD_OK"
        if score < 0.60:
            return "STAGE_ONLY"
        return "REVIEW"

    # 5. Fallback for UNKNOWN / missing decisions
    if score < 0.30:
        return "REVIEW"
    return "BLOCK"


def dominant_components(instab: dict) -> list[dict]:
    comp_names = [
        ("safety", "safety_component"),
        ("quality", "quality_component"),
        ("rdsi", "rdsi_component"),
        ("epf", "epf_component"),
    ]

    values = []
    for name, key in comp_names:
        val = float(instab.get(key, 0.0) or 0.0)
        if val > 0.0:
            values.append((name, val))

    # sort by descending contribution
    values.sort(key=lambda x: x[1], reverse=True)
    values = values[:2]  # top 2

    results: list[dict] = []
    for name, value in values:
        if name == "safety":
            reason = "One or more safety gates failed."
        elif name == "quality":
            reason = "One or more product-quality gates failed."
        elif name == "rdsi":
            reason = "RDSI below target threshold, decision stability degraded."
        elif name == "epf":
            reason = "EPF contraction above ideal; local adaptation may be unstable."
        else:
            reason = ""
        results.append(
            {
                "name": name,
                "value": value,
                "reason": reason,
            }
        )
    return results


def build_decision_trace(stability_map: dict, state: dict) -> dict:
    decision = state.get("decision") or "UNKNOWN"
    state_type = state.get("type") or "UNSTABLE"

    # Instability + score
    instab = state.get("instability") or {}
    score = float(instab.get("score", 0.0) or 0.0)

    # Az instability payloadban ezek a kulcsok vannak:
    #   safety_component, quality_component, rdsi_component, epf_component
    # Ezeket térképezzük át a schema szerinti nevekre:
    instability_components = {
        "safety": instab.get("safety_component"),
        "quality": instab.get("quality_component"),
        # a séma "rds1"-et vár, de az input "rdsi_component":
        "rds1": instab.get("rdsi_component"),
        "epf": instab.get("epf_component"),
    }

    # Delta curvature (mezőhajlítás) – optional
    delta_curv = state.get("delta_curvature") or {}
    delta_value = delta_curv.get("value")
    delta_band = delta_curv.get("band")

    # Gate- és EPF-információk
    gates = state.get("gate_summary") or {}
    epf = state.get("epf") or {}

    # Paradoxon jelenlét – ha nincs explicit flag, default: False
    paradox_present = bool(state.get("paradox_present", False))

    # Döntési szintű jelölések
    risk_level = compute_risk_level(score)
    action = decide_action(decision, state_type, score)
    dom = dominant_components(instab)

    # Új: stability_tag – külön jelzés a mezőhajlításra érzékeny „jó” döntésekre
    stability_tag: str | None = None
    if score < 0.30:
        # „jó” instabilitási tartomány
        if delta_band == "high":
            stability_tag = "unstably_good"
        else:
            stability_tag = "stable_good"

    component_str = ", ".join(
        f"{c['name']}={c['value']:.2f}" for c in dom
    ) or "none"

    summary = (
        f"{action}: {state_type} state with instability {score:.2f} "
        f"(risk={risk_level}, dominant components: {component_str})."
    )

    notes: list[str] = [
        f"Deterministic release decision: {decision}.",
        f"Stability type: {state_type}.",
        f"Instability score: {score:.3f} (risk level: {risk_level}).",
    ]

    if dom:
        notes.append(
            "Dominant instability components: "
            + ", ".join(f"{c['name']}={c['value']:.3f}" for c in dom)
        )

    if gates:
        notes.append(
            "Gate summary: "
            f"safety {gates.get('safety_failed', 0)}/{gates.get('safety_total', 0)} "
            f"failed, quality {gates.get('quality_failed', 0)}/{gates.get('quality_total', 0)} failed."
        )

    # Delta curvature-hez kapcsolódó megjegyzés – csak ha van értelmes jel
    if delta_value is not None and delta_band in {"medium", "high"}:
        band_label = delta_band.upper()
        notes.append(
            f"Delta curvature: {delta_value:.3f} ({band_label}); "
            "decision may be field-sensitive even if metrics look clean."
        )

    # Ha van stability_tag, azt is jegyezzük meg emberi nyelven
    if stability_tag is not None:
        notes.append(f"Stability tag: {stability_tag}.")

    # Alap, séma által várt mezők
    details: dict = {
        "release_decision": decision,
        "stability_type": state_type,
        "instability_score": score,
        "instability_components": instability_components,
        "gates": gates,
        "paradox_present": paradox_present,
        "epf": epf,
    }

    # Új, opcionális delta_curvature blokk – séma engedi (additionalProperties: true)
    if delta_value is not None:
        details["delta_curvature"] = {
            "value": float(delta_value),
            "band": delta_band,
        }

    # Új: gép-barát stability_tag is bekerül a details alá (opcionális)
    if stability_tag is not None:
        details["stability_tag"] = stability_tag

    # Extra, fejlesztőbarát mezők
    details["dominant_components"] = dom
    details["gate_summary"] = gates
    details["notes"] = notes

    trace = {
        "version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "state_id": state.get("id"),
        "action": action,
        "risk_level": risk_level,
        "summary": summary,
        "details": details,
    }
    return trace


def main():
    parser = argparse.ArgumentParser(description="PULSE Decision Engine v0")
    parser.add_argument(
        "--stability-map",
        type=Path,
        default=Path("PULSE_safe_pack_v0/artifacts/stability_map.json"),
        help="Path to stability_map.json",
    )
    parser.add_argument(
        "--state-id",
        type=str,
        default=None,
        help="Optional state id to evaluate; defaults to the first state",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("PULSE_safe_pack_v0/artifacts/decision_trace.json"),
        help="Output path for decision_trace.json",
    )
    args = parser.parse_args()

    stability_map = load_json(args.stability_map)
    state = select_state(stability_map, args.state_id)
    trace = build_decision_trace(stability_map, state)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, ensure_ascii=False)

    print(trace["summary"])


if __name__ == "__main__":
    main()
