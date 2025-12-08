#!/usr/bin/env python3
"""
print_status_summary.py

Small helper to print a human-readable summary for a PULSE status.json
artefact. This is meant as a quick check for developers and release owners.

The gate logic itself still lives in the safe-pack and in
PULSE_safe_pack_v0/tools/check_gates.py – this script is read-only.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_STATUS_PATH = Path("PULSE_safe_pack_v0") / "artifacts" / "status.json"


def load_status(path: Path) -> Dict[str, Any]:
    """Load status.json or exit with a clear error message."""
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"error: status file not found at {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: failed to parse JSON from {path}: {exc}")


def gate_label(value: bool) -> str:
    return "PASS" if value else "FAIL"


def get_nested(obj: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safe nested lookup: get_nested(status, 'model', 'id', default='-')."""
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def print_summary(status: Dict[str, Any]) -> None:
    """Print a compact, human-readable summary to stdout."""
    model_id = get_nested(status, "model", "id", default="-")
    profile = status.get("profile", "-")
    decision = status.get("decision", "-")

        # RDSI (Release Decision Stability Index)
    rds_lo = get_nested(status, "rds_index", "ci_lower")
    rds_hi = get_nested(status, "rds_index", "ci_upper")
    rds_value = get_nested(status, "rds_index", "value")

    if rds_lo is not None and rds_hi is not None:

        if rds_value is None:
            rds_value = (rds_lo + rds_hi) / 2.0

        lines.append(
            f"RDSI: {rds_value:.2f} (CI: {rds_lo:.2f}–{rds_hi:.2f})"
        )


    gates = status.get("gates", {}) or {}

    print("PULSE status summary")
    print("--------------------")
    print(f"Model:    {model_id}")
    print(f"Profile:  {profile}")
    print(f"Decision: {decision}")

    if rds_value is not None:
        if rds_lo is not None and rds_hi is not None:
            print(f"RDSI:    {rds_value:.3f} (CI: {rds_lo:.3f}–{rds_hi:.3f})")
        else:
            print(f"RDSI:    {rds_value:.3f}")
    print()

    interesting_gates = [
        "refusal_delta_pass",
        "external_all_pass",
        "quality_slo_pass",
        "overall_pass",
    ]

    print("Gates:")
    any_gate = False
    for name in interesting_gates:
        if name in gates:
            any_gate = True
            value = bool(gates.get(name))
            print(f"- {name}: {gate_label(value)}")

    if not any_gate:
        print("- (no gate booleans found in status['gates'])")

    failed = [name for name in interesting_gates if gates.get(name) is False]
    if failed:
        print()
        print(
            "One or more gates FAILED; "
            "see status.json and the Quality Ledger for details."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Print a human-readable summary for a PULSE status.json artefact."
        )
    )
    parser.add_argument(
        "--status",
        type=Path,
        default=DEFAULT_STATUS_PATH,
        help=f"path to status.json (default: {DEFAULT_STATUS_PATH})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    status = load_status(args.status)
    print_summary(status)


if __name__ == "__main__":
    main()
