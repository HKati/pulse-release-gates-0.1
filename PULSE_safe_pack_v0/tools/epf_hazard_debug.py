#!/usr/bin/env python3
"""
epf_hazard_debug.py

Small helper to introspect the EPF Relational Grail (hazard forecasting)
thresholds on a given environment.

It prints:
- whether a calibration artefact exists,
- what the artefact reports (sample count, global warn/crit),
- what HazardConfig() actually uses as warn/crit thresholds.

This is a developer-only tool; it does not change any gate behaviour.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, Optional, Tuple


def add_pack_to_sys_path() -> pathlib.Path:
    """
    Ensure PULSE_safe_pack_v0/ is on sys.path so we can import epf_hazard_forecast
    when running this script as:

        python PULSE_safe_pack_v0/tools/epf_hazard_debug.py
    """
    script_path = pathlib.Path(__file__).resolve()
    pack_root = script_path.parents[1]  # .../PULSE_safe_pack_v0
    if str(pack_root) not in sys.path:
        sys.path.insert(0, str(pack_root))
    return pack_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Debug the EPF hazard thresholds (baseline vs calibrated)."
    )
    parser.add_argument(
        "--calibration",
        type=pathlib.Path,
        default=None,
        help=(
            "Optional explicit path to a calibration JSON artefact. "
            "If omitted, uses the default path from epf_hazard_forecast."
        ),
    )
    return parser.parse_args()


def load_calibration_summary(path: pathlib.Path) -> Tuple[bool, Dict[str, Any]]:
    """
    Try to load a minimal summary from a calibration artefact:
    - present: bool
    - data: dict with 'warn', 'crit', 'count' (when available)
    """
    if not path.exists():
        return False, {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return True, {"error": "json_decode_error"}

    global_cfg = data.get("global", {})
    stats = global_cfg.get("stats", {}) or {}
    count = stats.get("count")
    warn = global_cfg.get("warn_threshold")
    crit = global_cfg.get("crit_threshold")

    summary: Dict[str, Any] = {}
    if count is not None:
        summary["count"] = count
    if warn is not None:
        summary["warn_threshold"] = warn
    if crit is not None:
        summary["crit_threshold"] = crit

    return True, summary


def main(argv: Optional[list[str]] = None) -> int:
    pack_root = add_pack_to_sys_path()

    # Import after we fixed sys.path
    from epf_hazard_forecast import (  # type: ignore
        HazardConfig,
        CALIBRATION_PATH,
        DEFAULT_WARN_THRESHOLD,
        DEFAULT_CRIT_THRESHOLD,
        MIN_CALIBRATION_SAMPLES,
    )

    args = parse_args()

    calibration_path = args.calibration or CALIBRATION_PATH

    print("EPF Relational Grail — hazard threshold debug")
    print("================================================")
    print(f"Pack root           : {pack_root}")
    print(f"Calibration file    : {calibration_path}")
    print(f"Min samples (guard) : {MIN_CALIBRATION_SAMPLES}")
    print()

    present, summary = load_calibration_summary(calibration_path)
    print("Baseline thresholds (built-in):")
    print(f"  warn_threshold = {DEFAULT_WARN_THRESHOLD:.4f}")
    print(f"  crit_threshold = {DEFAULT_CRIT_THRESHOLD:.4f}")
    print()

    if not present:
        print("Calibration artefact:")
        print("  <not found>")
    else:
        print("Calibration artefact:")
        if "error" in summary:
            print(f"  error: {summary['error']}")
        else:
            count = summary.get("count", "<missing>")
            warn = summary.get("warn_threshold", "<missing>")
            crit = summary.get("crit_threshold", "<missing>")
            print(f"  stats.count        = {count}")
            print(f"  global.warn_thresh = {warn}")
            print(f"  global.crit_thresh = {crit}")
    print()

    cfg = HazardConfig()
    print("Effective HazardConfig() thresholds:")
    print(f"  warn_threshold = {cfg.warn_threshold:.4f}")
    print(f"  crit_threshold = {cfg.crit_threshold:.4f}")
    print()

    # Quick note on whether we are using baseline or calibrated.
    using_baseline = (
        abs(cfg.warn_threshold - DEFAULT_WARN_THRESHOLD) < 1e-9
        and abs(cfg.crit_threshold - DEFAULT_CRIT_THRESHOLD) < 1e-9
    )
    if using_baseline:
        print("Decision:")
        print("  Using BASELINE thresholds (calibration missing/insufficient).")
    else:
        print("Decision:")
        print("  Using CALIBRATED thresholds from artefact.")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
