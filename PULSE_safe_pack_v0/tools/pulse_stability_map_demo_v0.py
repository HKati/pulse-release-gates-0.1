#!/usr/bin/env python3
"""
pulse_stability_map_demo_v0.py

Build a tiny stability_map_v0 demo artefact for the (Q3, Q4, EPF) 2×2 cell
described in docs/PULSE_topology_v0_mini_example_fairness_slo_epf.md.

This is a pure demo: it does NOT read real status.json files and does not
affect CI. It serves as a reference for how to embed Δ-curvature and tags
in stability_map_v0.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
from typing import Dict


def build_demo_stability_map() -> Dict:
    """Construct an in-memory demo stability_map_v0 structure."""

    # Synthetic run ids; in a real pipeline these would be actual PULSE run ids.
    runs = {
        "x00": "run_loose_epf0",
        "x10": "run_strict_epf0",
        "x01": "run_loose_epf1",
        "x11": "run_strict_epf1",
    }

    # Gate values as in the mini example doc.
    q3_values = {"x00": 0, "x10": 1, "x01": 0, "x11": 1}
    q4_values = {"x00": 1, "x10": 0, "x01": 0, "x11": 0}

    # Discrete derivatives on fairness axis a for each b.
    delta_a_q3_b0 = q3_values["x10"] - q3_values["x00"]
    delta_a_q3_b1 = q3_values["x11"] - q3_values["x01"]
    K_q3 = delta_a_q3_b1 - delta_a_q3_b0

    delta_a_q4_b0 = q4_values["x10"] - q4_values["x00"]
    delta_a_q4_b1 = q4_values["x11"] - q4_values["x01"]
    K_q4 = delta_a_q4_b1 - delta_a_q4_b0

    delta_bend = max(abs(K_q3), abs(K_q4))

    cell = {
        "id": "cell_fairness_slo_epf_demo",
        "profile": "prod_v_demo",
        "dataset_snapshot": "logs_demo_2025Q1",

        "axes": {
            "a": {"name": "fairness_threshold", "values": [0, 1]},
            "b": {"name": "epf_enabled", "values": [0, 1]},
        },

        "runs": runs,

        "gates": {
            "q3_fairness_ok": {
                "values": q3_values,
                "delta_a_b0": delta_a_q3_b0,
                "delta_a_b1": delta_a_q3_b1,
                "K": K_q3,
            },
            "q4_slo_ok": {
                "values": q4_values,
                "delta_a_b0": delta_a_q4_b0,
                "delta_a_b1": delta_a_q4_b1,
                "K": K_q4,
            },
        },

        "delta_bend": delta_bend,
        "tags": ["topology_demo_v0", "fairness_vs_slo", "epf_interaction"],
    }

    now = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    return {
        "stability_map_v0": {
            "version": "PULSE_stability_map_v0_demo",
            "generated_at_utc": now,
            "cells": [cell],
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a tiny stability_map_v0 demo artefact for the "
            "fairness–SLO–EPF Topology v0 example.\n"
            "This is demo-only and does not read real status.json files."
        )
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("stability_map_v0_demo.json"),
        help="Output JSON file for the demo stability_map_v0 artefact.",
    )

    args = parser.parse_args()

    stability_map = build_demo_stability_map()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(stability_map, f, indent=2, sort_keys=True)

    print(f"[PULSE] stability_map_v0 demo written to {args.output}")


if __name__ == "__main__":
    main()
