#!/usr/bin/env python
"""
g_child_stability_probe.py

Computes simple stability metrics across multiple g_field_v0.json runs.
Does not change any gates; it only produces a diagnostic overlay.
"""

import argparse
import datetime as _dt
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_g_field(path: Path) -> Tuple[Dict[str, Any], Dict[str, float]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    points_idx = {
        str(p["id"]): float(p["g_value"])
        for p in data.get("points", [])
        if "id" in p and "g_value" in p
    }
    return data, points_idx


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute stability metrics across multiple g_field_v0.json runs."
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="Paths to g_field_v0.json files from different runs.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for g_field_stability_v0.json.",
    )
    parser.add_argument(
        "--std-threshold",
        type=float,
        default=0.05,
        help="Std deviation threshold to mark a point as 'stable'. Default: 0.05",
    )
    args = parser.parse_args()

    if len(args.inputs) < 2:
        sys.stderr.write("[ERROR] Need at least two inputs for stability probe.\n")
        sys.exit(1)

    paths = [Path(p) for p in args.inputs]
    for p in paths:
        if not p.is_file():
            sys.stderr.write(f"[ERROR] Input not found: {p}\n")
            sys.exit(1)

    runs: List[Dict[str, float]] = []
    for p in paths:
        _, idx = _load_g_field(p)
        runs.append(idx)

    # Közös ID-k, amiket minden futásban látunk
    common_ids = set(runs[0].keys())
    for r in runs[1:]:
        common_ids &= set(r.keys())

    points_out = []
    std_values = []

    for pid in sorted(common_ids):
        vals = [r[pid] for r in runs]
        mean = statistics.fmean(vals)
        std = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        std_values.append(std)
        points_out.append(
            {
                "id": pid,
                "mean_g": mean,
                "std_g": std,
                "is_stable": std <= args.std_threshold,
            }
        )

    num_points = len(points_out)
    if std_values:
        mean_std = statistics.fmean(std_values)
        max_std = max(std_values)
        stable_fraction = sum(1 for s in std_values if s <= args.std_threshold) / num_points
    else:
        mean_std = None
        max_std = None
        stable_fraction = None

    created_at = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    out = {
        "version": "g_field_stability_v0",
        "created_at": created_at,
        "num_runs": len(paths),
        "num_points": num_points,
        "std_threshold_for_stable": args.std_threshold,
        "overall": {
            "mean_std": mean_std,
            "max_std": max_std,
            "stable_fraction": stable_fraction,
        },
        "points": points_out,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    sys.stderr.write(
        f"[INFO] Wrote g_field_stability_v0 overlay with {num_points} points to {out_path}\n"
    )


if __name__ == "__main__":
    main()
