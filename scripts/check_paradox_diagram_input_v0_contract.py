#!/usr/bin/env python3
"""
Contract checker for PULSE_safe_pack_v0/artifacts/paradox_diagram_input_v0.json.

Goal:
- Provide a stable, machine-readable input contract for future paradox diagram generation.
- Catch regressions in shape/types early.
- This checker is intentionally stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict


def _die(msg: str) -> None:
    print(f"[contract:error] {msg}", file=sys.stderr)
    raise SystemExit(2)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _die(f"Input file not found: {path}")
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON: {path} ({e})")
    return {}  # unreachable


def _require_key(d: Dict[str, Any], key: str) -> Any:
    if key not in d:
        _die(f"Missing required key: {key}")
    return d[key]


def _expect_dict(name: str, v: Any) -> Dict[str, Any]:
    if not isinstance(v, dict):
        _die(f"Expected '{name}' to be object, got {type(v).__name__}")
    return v


def _expect_bool(name: str, v: Any) -> None:
    if not isinstance(v, bool):
        _die(f"Expected '{name}' to be boolean, got {type(v).__name__}")


def _expect_str(name: str, v: Any) -> None:
    if not isinstance(v, str):
        _die(f"Expected '{name}' to be string, got {type(v).__name__}")
    if not v.strip():
        _die(f"Expected '{name}' to be non-empty string")


def _expect_str_or_none(name: str, v: Any) -> None:
    if v is None:
        return
    if not isinstance(v, str):
        _die(f"Expected '{name}' to be string|null, got {type(v).__name__}")


def _expect_number_ge0(name: str, v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        _die(f"Expected '{name}' to be number, got {type(v).__name__}")
    f = float(v)
    if not math.isfinite(f):
        _die(f"Expected '{name}' to be finite number, got {v}")
    if f < 0:
        _die(f"Expected '{name}' to be >= 0, got {v}")
    return f


def _expect_number_0_1(name: str, v: Any) -> float:
    if isinstance(v, bool):
        _die(f"Expected '{name}' to be number, got bool")
    if not isinstance(v, (int, float)):
        _die(f"Expected '{name}' to be number, got {type(v).__name__}")
    fv = float(v)
    if not (0.0 <= fv <= 1.0):
        _die(f"Expected '{name}' in [0,1], got {fv}")
    return fv


def validate(d: Dict[str, Any]) -> None:
    schema_version = _require_key(d, "schema_version")
    _expect_str("schema_version", schema_version)
    if schema_version != "v0":
        _die(f"Unsupported schema_version: {schema_version} (expected 'v0')")

    timestamp_utc = _require_key(d, "timestamp_utc")
    _expect_str("timestamp_utc", timestamp_utc)

    shadow = _require_key(d, "shadow")
    _expect_bool("shadow", shadow)

    decision_key = _require_key(d, "decision_key")
    _expect_str("decision_key", decision_key)
    if decision_key not in ("NORMAL", "WARN", "FAIL", "UNKNOWN"):
        _die(f"Invalid decision_key: {decision_key}")

    decision_raw = _require_key(d, "decision_raw")
    _expect_str("decision_raw", decision_raw)

    # Optional metadata
    if "source" in d:
        _expect_str_or_none("source", d.get("source"))
    if "notes" in d:
        _expect_str_or_none("notes", d.get("notes"))

    metrics = _require_key(d, "metrics")
    m = _expect_dict("metrics", metrics)

    settle_p95 = _require_key(m, "settle_time_p95_ms")
    settle_budget = _require_key(m, "settle_time_budget_ms")
    derr = _require_key(m, "downstream_error_rate")
    pd = _require_key(m, "paradox_density")

    _expect_number_ge0("metrics.settle_time_p95_ms", settle_p95)
    _expect_number_ge0("metrics.settle_time_budget_ms", settle_budget)
    _expect_number_0_1("metrics.downstream_error_rate", derr)
    _expect_number_0_1("metrics.paradox_density", pd)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Contract check: paradox diagram input v0")
    p.add_argument(
        "--in",
        dest="inp",
        default="PULSE_safe_pack_v0/artifacts/paradox_diagram_input_v0.json",
        help="Path to paradox_diagram_input_v0.json",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    path = Path(args.inp)
    d = _load_json(path)
    if not isinstance(d, dict):
        _die(f"Top-level JSON must be an object, got {type(d).__name__}")
    validate(d)
    print(f"OK: contract valid ({path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
