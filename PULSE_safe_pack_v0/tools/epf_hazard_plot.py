#!/usr/bin/env python3
"""
epf_hazard_plot.py

Small helper to visualise the EPF hazard JSONL log produced by
epf_hazard_adapter / run_all.py.

It reads epf_hazard_log.jsonl, filters by gate_id, and plots the
evolution of T(t), S(t), D(t) and E(t) over log index.

Usage:

    python PULSE_safe_pack_v0/tools/epf_hazard_plot.py
    python PULSE_safe_pack_v0/tools/epf_hazard_plot.py --log path/to/log.jsonl
    python PULSE_safe_pack_v0/tools/epf_hazard_plot.py --gate EPF_demo_RDSI
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, List


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot EPF hazard JSONL log (T, S, D, E over time)."
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
    parser.add_argument(
        "--gate",
        type=str,
        default=None,
        help=(
            "Gate/field id to plot (gate_id in the log). "
            "Defaults to the first gate_id found in the log."
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


def filter_by_gate(
    entries: List[Dict[str, Any]],
    gate_id: str | None,
) -> tuple[str, List[Dict[str, Any]]]:
    if not entries:
        return "", []

    if gate_id is None:
        # Pick first gate_id in the log.
        first = entries[0]
        gate_id = str(first.get("gate_id", "UNKNOWN"))

    filtered = [e for e in entries if str(e.get("gate_id")) == gate_id]
    return gate_id, filtered


def extract_series(events: List[Dict[str, Any]]) -> Dict[str, List[float]]:
    xs: List[int] = []
    Ts: List[float] = []
    Ss: List[float] = []
    Ds: List[float] = []
    Es: List[float] = []

    for idx, ev in enumerate(events):
        hazard = ev.get("hazard", {})
        try:
            T = float(hazard.get("T"))
            S = float(hazard.get("S"))
            D = float(hazard.get("D"))
            E = float(hazard.get("E"))
        except (TypeError, ValueError):
            # Skip entries with missing or non-numeric fields.
            continue

        xs.append(idx)
        Ts.append(T)
        Ss.append(S)
        Ds.append(D)
        Es.append(E)

    return {
        "x": xs,
        "T": Ts,
        "S": Ss,
        "D": Ds,
        "E": Es,
    }


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print(
            "matplotlib is required to run this script. "
            "Install it with `pip install matplotlib`.",
            file=sys.stderr,
        )
        return 1

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
    if not entries:
        print(f"no entries found in log: {log_path}", file=sys.stderr)
        return 1

    gate_id, events = filter_by_gate(entries, args.gate)
    if not events:
        print(
            f"no events found for gate_id={gate_id!r} in {log_path}",
            file=sys.stderr,
        )
        return 1

    series = extract_series(events)
    if not series["x"]:
        print(
            f"no numeric hazard values for gate_id={gate_id!r} in {log_path}",
            file=sys.stderr,
        )
        return 1

    x = series["x"]
    T = series["T"]
    S = series["S"]
    D = series["D"]
    E = series["E"]

    print(
        f"Plotting EPF hazard series for gate_id={gate_id!r} "
        f"from log={str(log_path)!r} with {len(x)} points."
    )

    fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True)
    fig.suptitle(f"EPF hazard time series — gate_id={gate_id}", fontsize=14)

    axes[0].plot(x, E)
    axes[0].set_ylabel("E(t)")
    axes[0].grid(True, linestyle=":", linewidth=0.5)

    axes[1].plot(x, T)
    axes[1].set_ylabel("T(t)")
    axes[1].grid(True, linestyle=":", linewidth=0.5)

    axes[2].plot(x, S)
    axes[2].set_ylabel("S(t)")
    axes[2].set_ylim(0.0, 1.0)
    axes[2].grid(True, linestyle=":", linewidth=0.5)

    axes[3].plot(x, D)
    axes[3].set_ylabel("D(t)")
    axes[3].set_xlabel("log index")
    axes[3].grid(True, linestyle=":", linewidth=0.5)

    plt.tight_layout()
    plt.show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
