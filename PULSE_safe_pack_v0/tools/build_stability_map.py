#!/usr/bin/env python3
"""
PULSE Stability Map builder v0

This script builds a minimal stability_map.json from a single run's
status.json + optional status_epf.json artefacts.

v0 integrates:
- basic instability scores and state types
- Paradox Module v0 (pattern detection)
- Paradox Resolution v0 (triage + recommendations)
"""

import json
from pathlib import Path
from datetime import datetime, timezone
import argparse


def load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def summarize_gates(status: dict):
    """Summarise gates into safety / quality counts.

    Expected shape (loosely):

        status["gates"] ~ {
            gate_name: {
                "status": "PASS" / "FAIL",
                "group": "safety" / "quality" / ...
            }
        }

    If "group" is missing, we guess from the gate name.
    """
    gates = status.get("gates", {}) or {}

    safety_total = safety_failed = 0
    quality_total = quality_failed = 0

    for name, gate in gates.items():
        group = gate.get("group")
        if group is None:
            lower = name.lower()
            if "safety" in lower:
                group = "safety"
            elif "quality" in lower:
                group = "quality"
            else:
                # default bucket if no explicit group
                group = "safety"

        status_str = str(gate.get("status", "")).upper()
        passed = status_str == "PASS"

        if group == "safety":
            safety_total += 1
            if not passed:
                safety_failed += 1
        elif group == "quality":
            quality_total += 1
            if not passed:
                quality_failed += 1

    return {
        "safety_total": safety_total,
        "safety_failed": safety_failed,
        "quality_total": quality_total,
        "quality_failed": quality_failed,
    }


def compute_instability(status: dict, status_epf: dict | None):
    """Compute instability score v0.

    Components:
    - safety_failed / safety_total
    - quality_failed / quality_total
    - RDSI deviation from target
    - EPF contraction component (if available)
    """
    gates = summarize_gates(status)
    safety_total = gates["safety_total"]
    safety_failed = gates["safety_failed"]
    quality_total = gates["quality_total"]
    quality_failed = gates["quality_failed"]

    safety_ratio = safety_failed / safety_total if safety_total else 0.0
    quality_ratio = quality_failed / quality_total if quality_total else 0.0

    # TODO: adjust to actual key name if different
    rdsi = (
        status.get("rdsi")
        or status.get("RDSI")
        or status.get("metrics", {}).get("rdsi", 1.0)
    )
    rdsi_target = 0.9
    rdsi_component = max(0.0, (rdsi_target - rdsi) / rdsi_target)

    epf_available = status_epf is not None
    epf_L = None
    epf_component = 0.0
    epf_shadow_pass = None

    if epf_available:
        metrics = status_epf.get("metrics", {})
        epf_L = metrics.get("epf_L")
        epf_shadow_pass = metrics.get("shadow_pass")
        if epf_L is not None:
            epf_L_max = 1.2
            epf_component = max(0.0, (epf_L - 1.0) / epf_L_max)

    # Weights v0 – can be tuned
    w_safety = 0.4
    w_quality = 0.2
    w_rdsi = 0.2
    w_epf = 0.2

    instability_score = (
        w_safety * safety_ratio
        + w_quality * quality_ratio
        + w_rdsi * rdsi_component
        + w_epf * epf_component
    )

    components = {
        "score": instability_score,
        "safety_component": w_safety * safety_ratio,
        "quality_component": w_quality * quality_ratio,
        "rdsi_component": w_rdsi * rdsi_component,
        "epf_component": w_epf * epf_component,
    }

    epf_meta = {
        "available": epf_available,
        "L": epf_L,
        "shadow_pass": epf_shadow_pass,
    }

    return gates, components, epf_meta, rdsi


def classify_type(decision: str, instability_score: float,
                  safety_failed: int, quality_failed: int) -> str:
    """State-type classification v0."""
    decision = (decision or "").upper()

    # Example paradox-like pattern: safety OK, quality failing
    if safety_failed == 0 and quality_failed > 0:
        return "PARADOX"

    if decision == "PROD-PASS" and instability_score < 0.3:
        return "STABLE"
    if decision in {"STAGE-PASS", "PROD-PASS"} and instability_score < 0.6:
        return "METASTABLE"
    if instability_score >= 0.85:
        return "COLLAPSE"

    return "UNSTABLE"


def detect_paradox(state: dict) -> dict:
    """Detect simple paradox patterns on top of a ReleaseState.

    Implements v0 patterns from docs/PULSE_paradox_module_v0.md:
    - SAFETY_QUALITY_CONFLICT
    - DECISION_SCORE_CONFLICT
    - EPF_DECISION_CONFLICT
    """
    gs = state.get("gate_summary") or {}
    instab = state.get("instability") or {}
    epf = state.get("epf") or {}
    decision = (state.get("decision") or "").upper()

    patterns: list[str] = []
    details: list[dict] = []

    # 1. SAFETY_QUALITY_CONFLICT
    if gs.get("safety_failed", 0) == 0 and gs.get("quality_failed", 0) > 0:
        patterns.append("SAFETY_QUALITY_CONFLICT")
        details.append(
            {
                "pattern": "SAFETY_QUALITY_CONFLICT",
                "reason": "No safety gate failures, but one or more quality gates failed.",
            }
        )

    # 2. DECISION_SCORE_CONFLICT
    score = float(instab.get("score", 0.0) or 0.0)
    if decision in {"STAGE-PASS", "PROD-PASS"} and score >= 0.85:
        patterns.append("DECISION_SCORE_CONFLICT")
        details.append(
            {
                "pattern": "DECISION_SCORE_CONFLICT",
                "reason": "Release decision is PASS while instability score is collapse-level.",
            }
        )

    # 3. EPF_DECISION_CONFLICT
    epf_L = epf.get("L")
    if (
        epf.get("available") is True
        and decision in {"STAGE-PASS", "PROD-PASS"}
        and epf_L is not None
        and epf_L > 1.0
    ):
        patterns.append("EPF_DECISION_CONFLICT")
        details.append(
            {
                "pattern": "EPF_DECISION_CONFLICT",
                "reason": "Release decision is PASS while EPF indicates non-contractive behaviour.",
            }
        )

    present = len(patterns) > 0

    if not present:
        return {"present": False, "patterns": []}

    return {
        "present": True,
        "patterns": patterns,
        "details": details,
    }


def build_paradox_resolution(state: dict) -> dict | None:
    """Build Paradox Resolution v0 plan for a given state.

    Implements the heuristics from docs/PULSE_paradox_resolution_v0.md.
    """
    paradox = state.get("paradox") or {}
    if not paradox.get("present"):
        return None

    patterns = paradox.get("patterns") or []
    instab = state.get("instability") or {}
    score = float(instab.get("score", 0.0) or 0.0)
    decision = (state.get("decision") or "").upper()
    epf_L = (state.get("epf") or {}).get("L")

    plans: list[dict] = []

    # SAFETY_QUALITY_CONFLICT
    if "SAFETY_QUALITY_CONFLICT" in patterns:
        sev = "MEDIUM" if score < 0.6 else "HIGH"
        plans.append(
            {
                "severity": sev,
                "primary_focus": ["quality", "policy", "data"],
                "recommendations": [
                    "Inspect failing quality gates and identify which dimensions are off.",
                    "Check whether recent policy or refusal changes conflict with quality metrics.",
                    "Review training/eval datasets for coverage gaps related to failing quality gates.",
                ],
            }
        )

    # DECISION_SCORE_CONFLICT
    if "DECISION_SCORE_CONFLICT" in patterns:
        plans.append(
            {
                "severity": "HIGH",
                "primary_focus": ["safety", "governance", "data", "training"],
                "recommendations": [
                    "Revisit release criteria: why does the gate logic permit PASS at collapse-level instability?",
                    "Review recently added capabilities or prompts that may push the system into unstable regimes.",
                    "Consider adding or tightening safety/quality gates targeting this region of behaviour.",
                ],
            }
        )

    # EPF_DECISION_CONFLICT
    if "EPF_DECISION_CONFLICT" in patterns:
        if decision == "PROD-PASS":
            sev = "HIGH"
        else:
            # STAGE-PASS or other
            if epf_L is not None and epf_L > 1.1:
                sev = "HIGH"
            else:
                sev = "MEDIUM"
        plans.append(
            {
                "severity": sev,
                "primary_focus": ["epf", "training", "policy"],
                "recommendations": [
                    "Inspect EPF trajectories for this configuration and locate non-contractive regions.",
                    "Consider tightening or reshaping training objectives in the EPF-flagged region.",
                    "Re-evaluate policy or refusal rules that interact with the unstable EPF regime.",
                ],
            }
        )

    if not plans:
        return None

    # Merge severity (LOW < MEDIUM < HIGH)
    order = ["LOW", "MEDIUM", "HIGH"]
    sev_idx = max(order.index(p["severity"]) for p in plans)
    severity = order[sev_idx]

    # Merge primary_focus, de-duplicated
    primary_focus: list[str] = []
    for p in plans:
        for f in p["primary_focus"]:
            if f not in primary_focus:
                primary_focus.append(f)

    # Merge recommendations (keep first 6)
    recommendations: list[str] = []
    for p in plans:
        recommendations.extend(p["recommendations"])
    recommendations = recommendations[:6]

    return {
        "severity": severity,
        "primary_focus": primary_focus,
        "recommendations": recommendations,
    }


def build_stability_map(status_path: Path, status_epf_path: Path | None, out_path: Path):
    status = load_json(status_path)
    if status is None:
        raise SystemExit(f"Nem találom a status.json-t: {status_path}")

    status_epf = load_json(status_epf_path) if status_epf_path is not None else None

    gates, instab_components, epf_meta, rdsi = compute_instability(status, status_epf)

    # TODO: adjust to actual decision / release-level key
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

    # Paradox detection v0
    paradox_info = detect_paradox(state)
    state["paradox"] = paradox_info

    if paradox_info.get("present") and state["type"] != "COLLAPSE":
        state["type"] = "PARADOX"

    # Paradox Resolution v0
    resolution = build_paradox_resolution(state)
    if resolution:
        state.setdefault("paradox", {})["resolution"] = resolution

    stability_map = {
        "version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "states": [state],
        "transitions": [],  # v0: single run; history comes later
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(stability_map, f, indent=2, ensure_ascii=False)

    print(f"stability_map.json elkészült: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="PULSE Stability Map builder v0")
    parser.add_argument(
        "--status",
        type=Path,
        default=Path("PULSE_safe_pack_v0/artifacts/status.json"),
        help="PULSE status.json elérési útja",
    )
    parser.add_argument(
        "--status-epf",
        type=Path,
        default=Path("PULSE_safe_pack_v0/artifacts/status_epf.json"),
        help="EPF status_epf.json elérési útja (opcionális)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("PULSE_safe_pack_v0/artifacts/stability_map.json"),
        help="kimeneti stability_map.json elérési útja",
    )

    args = parser.parse_args()
    build_stability_map(args.status, args.status_epf, args.out)


if __name__ == "__main__":
    main()
