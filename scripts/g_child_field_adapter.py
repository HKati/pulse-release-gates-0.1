#!/usr/bin/env python
"""
g_child_field_adapter.py

HPC G-gyerek snapshotokból egységes g_field_v0.json overlay-t készít
a PULSE topológia réteg számára. Nem módosít semmilyen gate-et,
nem érinti a CI viselkedését.
"""

import argparse
import datetime as _dt
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                sys.stderr.write(
                    f"[WARN] Invalid JSON on line {line_no} in {path}, skipping.\n"
                )


def _load_snapshots(path: Path) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    for rec in _iter_jsonl(path):
        id_ = rec.get("id") or rec.get("trace_id") or rec.get("sample_id")
        g_val = (
            rec.get("g_value")
            if "g_value" in rec
            else rec.get("g")
        )

        if id_ is None or g_val is None:
            # HPC formátum még nincs véglegesítve -> warning + skip
            sys.stderr.write(
                "[WARN] Snapshot record without id or g_value/g; skipping: "
                f"{json.dumps(rec, ensure_ascii=False)[:200]}\n"
            )
            continue

        try:
            g_float = float(g_val)
        except (TypeError, ValueError):
            sys.stderr.write(
                f"[WARN] Non-numeric g_value for id={id_!r}; skipping.\n"
            )
            continue

        points.append({"id": str(id_), "g_value": g_float})
    return points


def _load_status_run_id(path: Optional[Path]) -> Optional[str]:
    if path is None or not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            status = json.load(f)
    except Exception:
        return None

    # Ha van explicit run_id, használjuk, különben None
    return (
        status.get("run_id")
        or status.get("meta", {}).get("run_id")
        or None
    )


def _build_g_field(points: List[Dict[str, Any]], run_id: Optional[str]) -> Dict[str, Any]:
    values = [p["g_value"] for p in points]
    num_points = len(values)

    if num_points:
        g_mean = statistics.fmean(values)
        g_std = statistics.pstdev(values) if num_points > 1 else 0.0
    else:
        g_mean = None
        g_std = None

    created_at = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    return {
        "version": "g_field_v0",
        "source": "internal_hpc_g_child",
        "created_at": created_at,
        "run_id": run_id,
        "summary": {
            "num_points": num_points,
            "g_mean": g_mean,
            "g_std": g_std,
        },
        "points": points,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adapt HPC G-child snapshots into g_field_v0.json overlay."
    )
    parser.add_argument(
        "--snapshots",
        required=True,
        help="Input JSONL file with HPC G snapshots (id + g_value/g).",
    )
    parser.add_argument(
        "--status",
        required=False,
        help="Optional PULSE status.json path (for run_id).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for g_field_v0.json.",
    )
    args = parser.parse_args()

    snapshots_path = Path(args.snapshots)
    if not snapshots_path.is_file():
        sys.stderr.write(f"[ERROR] Snapshots file not found: {snapshots_path}\n")
        sys.exit(1)

    status_path = Path(args.status) if args.status else None
    points = _load_snapshots(snapshots_path)
    run_id = _load_status_run_id(status_path)

    g_field = _build_g_field(points, run_id)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(g_field, f, ensure_ascii=False, indent=2)

    sys.stderr.write(
        f"[INFO] Wrote g_field_v0 overlay with {len(points)} points to {out_path}\n"
    )


if __name__ == "__main__":
    main()
