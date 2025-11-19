#!/usr/bin/env python
"""
summarise_decision_history_v0.py

Aggregate multiple decision_output_v0.json files into a single
decision_history_v0.json.

Input:
    - a directory with one or more decision_output_v0*.json files
      (produced by build_decision_output_v0.py)

Output:
    - decision_history_v0.json (by default), containing:
        - per-run records (decision, type, rdsi, instability_score)
        - aggregated decision/type counts
        - basic stats for rdsi and instability_score

This is a generic decision history view, independent of the EPF/paradox
field, but built on top of the same Decision Engine v0 shadow output.
"""

import argparse
import glob
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


DecisionOutput = Dict[str, Any]
History = Dict[str, Any]


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _avg(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    return sum(vals) / len(vals)


def _update_counts(counts: Dict[str, int], key: Optional[str]) -> None:
    if key is None:
        key = "NULL"
    counts[key] = counts.get(key, 0) + 1


def load_decision_outputs(dir_path: str, pattern: str) -> List[DecisionOutput]:
    glob_pattern = os.path.join(dir_path, pattern)
    paths = sorted(glob.glob(glob_pattern))
    outputs: List[DecisionOutput] = []

    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                outputs.append(json.load(f))
        except (OSError, json.JSONDecodeError):
            # v0: silently skip invalid files
            continue

    return outputs


def build_decision_history_v0(outputs: List[DecisionOutput]) -> History:
    runs: List[Dict[str, Any]] = []
    decision_counts: Dict[str, int] = {}
    type_counts: Dict[str, int] = {}

    rdsi_vals: List[float] = []
    instab_vals: List[float] = []

    for d in outputs:
        if not isinstance(d, dict):
            continue

        run_id = d.get("run_id")
        decision = d.get("decision")

        release_state = d.get("release_state") or {}
        type_ = release_state.get("type")

        rdsi = _safe_float(release_state.get("rdsi"))

        instability = release_state.get("instability") or {}
        instab = _safe_float(instability.get("score"))

        runs.append(
            {
                "run_id": run_id,
                "decision": decision,
                "type": type_,
                "rdsi": rdsi,
                "instability_score": instab,
            }
        )

        _update_counts(decision_counts, decision)
        _update_counts(type_counts, type_)

        if rdsi is not None:
            rdsi_vals.append(rdsi)
        if instab is not None:
            instab_vals.append(instab)

    rdsi_stats = {
        "min": min(rdsi_vals) if rdsi_vals else None,
        "max": max(rdsi_vals) if rdsi_vals else None,
        "avg": _avg(rdsi_vals),
    }
    instab_stats = {
        "min": min(instab_vals) if instab_vals else None,
        "max": max(instab_vals) if instab_vals else None,
        "avg": _avg(instab_vals),
    }

    history: History = {
        "version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "num_runs": len(runs),
        "runs": runs,
        "decision_counts": decision_counts,
        "type_counts": type_counts,
        "rdsi_stats": rdsi_stats,
        "instability_stats": instab_stats,
    }

    return history


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate multiple decision_output_v0*.json files "
            "into decision_history_v0.json"
        )
    )
    parser.add_argument(
        "--dir",
        dest="dir_path",
        default=".",
        help="Directory containing decision_output_v0*.json files (default: .)",
    )
    parser.add_argument(
        "--pattern",
        dest="pattern",
        default="decision_output_v0*.json",
        help="Glob pattern for decision output files "
             '(default: "decision_output_v0*.json")',
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        default="decision_history_v0.json",
        help="Output JSON path (default: decision_history_v0.json)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    outputs = load_decision_outputs(args.dir_path, args.pattern)
    history = build_decision_history_v0(outputs)

    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    print(
        f"[decision_history_v0] aggregated {history['num_runs']} runs "
        f"into {args.out_path}"
    )


if __name__ == "__main__":
    main()
