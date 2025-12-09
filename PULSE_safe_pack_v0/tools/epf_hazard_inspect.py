#!/usr/bin/env python3
"""
epf_hazard_inspect.py

Small helper to inspect the EPF hazard JSONL log produced by
epf_hazard_adapter / run_all.py.

It reads epf_hazard_log.jsonl, groups entries by gate_id, and prints a
short summary (count, last zone, last E, min/max/mean E).

Usage:

    python PULSE_safe_pack_v0/tools/epf_hazard_inspect.py
    python PULSE_safe_pack_v0/tools/epf_hazard_inspect.py --log path/to/log.jsonl
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
from typing import Any, Dict, List


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect EPF hazard JSONL log and print a summary."
    )
    parser.add_argument(
        "--log",
        type=pathlib.Path,
        default=None,
        help=(
            "Path to epf_hazard_log.jsonl. "
            "Defaults to PULSE_safe_pack_v0/artifacts/epf_hazard_log.jsonl."
        ),
    )
    return parser.parse_args(argv)


def load_entries(path: pathlib.Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            entries.append(obj)
    return entries


def summarize(entries: List[Dict[str, Any]]) -> None:
    if not entries:
        print("No hazard entries found.")
        return

    # Group by gate_id
    by_gate: Dict[str, List[Dict[str, Any]]] = {}
    for e in entries:
        gate_id = str(e.get("gate_id", "UNKNOWN"))
        by_gate.setdefault(gate_id, []).append(e)

    print(f"Total hazard entries: {len(entries)}")
    print(f"Gates / fields: {len(by_gate)}")
    print()

    for gate_id, events in sorted(by_gate.items()):
        es: List[float] = []
        zones: List[str] = []
        last_ts = None
        last_e = None
        last_zone = None

        for ev in events:
            hazard = ev.get("hazard", {})
            E = hazard.get("E")
            zone = hazard.get("zone")
            ts = ev.get("timestamp")
            if isinstance(E, (int, float)):
                es.append(float(E))
                last_e = float(E)
            if isinstance(zone, str):
                zones.append(zone)
                last_zone = zone
            if isinstance(ts, str):
                last_ts = ts

        if not es:
            print(f"[{gate_id}] no numeric E values, skipping.")
            continue

        try:
            mean_e = statistics.mean(es)
        except statistics.StatisticsError:
            mean_e = es[0]

        min_e = min(es)
        max_e = max(es)

        print(f"[{gate_id}]")
        print(f"  entries   : {len(events)}")
        if last_ts is not None:
            print(f"  last ts   : {last_ts}")
        if last_zone is not None and last_e is not None:
            print(f"  last zone : {last_zone} (E={last_e:.3f})")
        print(f"  E range   : min={min_e:.3f}, max={max_e:.3f}, mean={mean_e:.3f}")
        print()


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    if args.log is not None:
        log_path = args.log
    else:
        # Default to pack_root/artifacts/epf_hazard_log.jsonl
        script_path = pathlib.Path(__file__).resolve()
        pack_root = script_path.parents[1]
        log_path = pack_root / "artifacts" / "epf_hazard_log.jsonl"

    if not log_path.exists():
        print(f"hazard log not found: {log_path}", file=sys.stderr)
        return 1

    entries = load_entries(log_path)
    summarize(entries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
