#!/usr/bin/env python3
"""
pulse_decision_engine_v0.py

Decision Engine v0:

Read PULSE status.json and optional Topology v0 artefacts
(stability_map_v0, paradox_field_v0), and emit a decision_engine_v0
JSON overlay.

This is diagnostic-only. It does NOT change CI behaviour or the core
PULSE gates (check_gates.py remains the source of truth).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
from typing import Any, Dict, List, Optional


def _load_json(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _collect_gates_from_results(
    results: Dict[str, Any],
    prefix: str = "",
) -> Dict[str, bool]:
    """
    Recursively collect boolean fields as gates, using dotted names.

    Example:
      results["quality"]["q3_fairness_ok"] -> "quality.q3_fairness_ok"
    """
    gates: Dict[str, bool] = {}
    for key, value in results.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, bool):
            gates[name] = value
        elif isinstance(value, dict):
            gates.update(_collect_gates_from_results(value, name))
    return gates


def _summarise_status(status: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a coarse summary of the status.json gate field.

    We do NOT reimplement PULSE gating; this is a diagnostic snapshot:
      - gate_count
      - failed_gates[]
      - passed_gates[]
      - optional RDSI-ish metrics if present.
    """
    results = status.get("results", {})
    if not isinstance(results, dict):
        results = {}

    gates = _collect_gates_from_results(results)
    total = len(gates)
    failed = [name for name, ok in gates.items() if not ok]
    passed = [name for name, ok in gates.items() if ok]

    summary: Dict[str, Any] = {
        "gate_count": total,
        "failed_gates": failed,
        "passed_gates": passed,
    }

    # Optionally surface some known metrics if they exist.
    metrics = status.get("metrics", {})
    if isinstance(metrics, dict):
        for key in ("rdsi", "rdsi_ci_lower", "rdsi_ci_upper"):
            if key in metrics:
                summary[key] = metrics[key]

    return summary


def _summarise_stability_map(stability_map: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a coarse stability summary from a stability_map_v0 artefact.

    We assume a shape like:
      { "stability_map_v0": { "cells": [ { "delta_bend": ... }, ... ] } }
    but we also accept a root-level "cells" for robustness.
    """
    root = stability_map.get("stability_map_v0") or stability_map
    cells = root.get("cells", []) if isinstance(root, dict) else []
    cell_count = len(cells)
    delta_bend_values: List[float] = []

    for cell in cells:
        db = cell.get("delta_bend")
        try:
            if db is not None:
                delta_bend_values.append(float(db))
        except (TypeError, ValueError):
            continue

    delta_bend_max = max(delta_bend_values) if delta_bend_values else 0.0

    return {
        "cell_count": cell_count,
        "delta_bend_max": delta_bend_max,
    }


def _summarise_paradox_field(paradox_field: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a compact summary from paradox_field_v0:

      - atom_count
      - severe_atom_count (severity >= 0.8)
    """
    root = paradox_field.get("paradox_field_v0") or paradox_field
    atoms = root.get("atoms", []) if isinstance(root, dict) else []
    atom_count = len(atoms)
    severe_atoms = [
        a
        for a in atoms
        if isinstance(a, dict) and float(a.get("severity", 0.0)) >= 0.8
    ]

    return {
        "atom_count": atom_count,
        "severe_atom_count": len(severe_atoms),
    }


def _classify_release_state(status_summary: Dict[str, Any]) -> str:
    """
    Heuristic release_state classification based on gate failures.

    This does NOT override the real CI gating; it's a descriptive view:

      - PROD_OK     : no failed gates
      - STAGE_ONLY  : few failed gates (<= 1/4 of total, at least 1)
      - BLOCK       : many failed gates
      - UNKNOWN     : no gates found
    """
    failed = status_summary.get("failed_gates", [])
    total = status_summary.get("gate_count", 0)

    if total == 0:
        return "UNKNOWN"

    fail_count = len(failed)

    if fail_count == 0:
        return "PROD_OK"
    elif fail_count <= max(1, total // 4):
        return "STAGE_ONLY"
    else:
        return "BLOCK"


def _classify_stability_type(
    release_state: str,
    stability_summary: Optional[Dict[str, Any]],
    paradox_summary: Optional[Dict[str, Any]],
) -> str:
    """
    Classify a coarse stability_type using Topology v0 signals:

      - stable_good / unstably_good
      - stable_bad  / unstably_bad
      - boundary / boundary_simple
      - unknown

    Intuition:
      - any non-zero delta_bend or non-zero atom_count -> "has topology signal"
      - combine that with release_state to get the label.
    """
    delta_bend_max = 0.0
    atom_count = 0

    if stability_summary:
        try:
            delta_bend_max = float(stability_summary.get("delta_bend_max", 0.0))
        except (TypeError, ValueError):
            delta_bend_max = 0.0

    if paradox_summary:
        try:
            atom_count = int(paradox_summary.get("atom_count", 0))
        except (TypeError, ValueError):
            atom_count = 0

    has_topology_signal = (delta_bend_max > 0.0) or (atom_count > 0)

    if release_state == "PROD_OK":
        return "unstably_good" if has_topology_signal else "stable_good"
    elif release_state == "BLOCK":
        return "unstably_bad" if has_topology_signal else "stable_bad"
    elif release_state == "STAGE_ONLY":
        return "boundary" if has_topology_signal else "boundary_simple"
    else:
        return "unknown"


def build_decision(
    status_path: pathlib.Path,
    stability_map_path: Optional[pathlib.Path] = None,
    paradox_field_path: Optional[pathlib.Path] = None,
) -> Dict[str, Any]:
    """Build the decision_engine_v0 structure from the given artefacts."""
    status = _load_json(status_path)
    status_summary = _summarise_status(status)

    stability_summary: Optional[Dict[str, Any]] = None
    paradox_summary: Optional[Dict[str, Any]] = None

    if stability_map_path is not None:
        stability_map = _load_json(stability_map_path)
        stability_summary = _summarise_stability_map(stability_map)

    if paradox_field_path is not None:
        paradox_field = _load_json(paradox_field_path)
        paradox_summary = _summarise_paradox_field(paradox_field)

    release_state = _classify_release_state(status_summary)
    stability_type = _classify_stability_type(
        release_state, stability_summary, paradox_summary
    )

    now = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    decision = {
        "decision_engine_v0": {
            "version": "PULSE_decision_engine_v0",
            "generated_at_utc": now,
            "inputs": {
                "status_path": str(status_path),
                "stability_map_path": str(stability_map_path)
                if stability_map_path
                else None,
                "paradox_field_path": str(paradox_field_path)
                if paradox_field_path
                else None,
            },
            "release_state": release_state,
            "stability_type": stability_type,
            "status_summary": status_summary,
            "stability_summary": stability_summary,
            "paradox_summary": paradox_summary,
        }
    }

    return decision


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Decision Engine v0:\n"
            "Read PULSE status.json and optional Topology v0 artefacts "
            "(stability_map_v0, paradox_field_v0) and emit a decision_engine_v0 "
            "JSON overlay.\n"
            "This is diagnostic-only and does not affect CI or check_gates.py."
        )
    )
    parser.add_argument(
        "--status",
        type=pathlib.Path,
        required=True,
        help="Path to PULSE status.json artefact.",
    )
    parser.add_argument(
        "--stability-map",
        type=pathlib.Path,
        dest="stability_map",
        required=False,
        help="Optional path to stability_map_v0 JSON artefact.",
    )
    parser.add_argument(
        "--paradox-field",
        type=pathlib.Path,
        dest="paradox_field",
        required=False,
        help="Optional path to paradox_field_v0 JSON artefact.",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        required=True,
        help="Output JSON file for decision_engine_v0 artefact.",
    )

    args = parser.parse_args()

    decision = build_decision(
        status_path=args.status,
        stability_map_path=args.stability_map,
        paradox_field_path=args.paradox_field,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2, sort_keys=True)

    print(f"[PULSE] decision_engine_v0 written to {args.output}")


if __name__ == "__main__":
    main()
