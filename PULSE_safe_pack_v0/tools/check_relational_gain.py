#!/usr/bin/env python3
"""
PULSE check_relational_gain.py

Shadow-only relational gain checker.

Purpose:
- evaluate edge gains
- evaluate cycle gains
- emit a self-contained audit artifact
- fail closed at checker level when any gain exceeds 1.0

This checker is diagnostic-only in v0:
- it does not emit a normative gate under gates.*
- it does not change policy or release behavior by itself

Exit codes:
- 0: PASS or WARN
- 1: FAIL
- 2: invalid input / parse error / schema error / IO error
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CHECKER_VERSION = "relational_gain_v0"
DEFAULT_WARN_THRESHOLD = 0.95
DEFAULT_EDGE_KEY = "edge_gains"
DEFAULT_CYCLE_KEY = "cycle_gains"


@dataclass(frozen=True)
class RelationalGainResult:
    verdict: str
    max_edge_gain: float
    max_cycle_gain: float
    warn_threshold: float
    checked_edges: int
    checked_cycles: int
    offending_edges: list[float]
    offending_cycles: list[float]
    near_boundary_edges: list[float]
    near_boundary_cycles: list[float]


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _fail(msg: str) -> None:
    _eprint(f"[X] {msg}")
    raise SystemExit(2)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _fail(f"input file not found: {path}")
    except json.JSONDecodeError as e:
        _fail(f"invalid JSON at {path}: {e}")
    except OSError as e:
        _fail(f"failed to read {path}: {e}")

    if not isinstance(data, dict):
        _fail("input JSON must be an object")

    return data


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as e:
        _fail(f"failed to write {path}: {e}")


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _read_gain_list(container: dict[str, Any], key: str) -> tuple[bool, list[float]]:
    if key not in container:
        return False, []

    raw = container[key]
    if not isinstance(raw, list):
        _fail(f"expected '{key}' to be a list")

    out: list[float] = []
    for i, item in enumerate(raw):
        if not _is_finite_number(item):
            _fail(f"expected '{key}[{i}]' to be a finite number")
        out.append(abs(float(item)))

    return True, out


def _extract_gains(
    payload: dict[str, Any],
    edge_key: str,
    cycle_key: str,
) -> tuple[list[float], list[float]]:
    metrics = payload.get("metrics")
    nested: dict[str, Any] = {}
    if isinstance(metrics, dict):
        maybe_nested = metrics.get("relational_gain")
        if isinstance(maybe_nested, dict):
            nested = maybe_nested

    top_edge_found, top_edge_gains = _read_gain_list(payload, edge_key)
    top_cycle_found, top_cycle_gains = _read_gain_list(payload, cycle_key)

    nested_edge_found, nested_edge_gains = _read_gain_list(nested, edge_key)
    nested_cycle_found, nested_cycle_gains = _read_gain_list(nested, cycle_key)

    if top_edge_found and nested_edge_found:
        _fail(
            f"ambiguous schema: '{edge_key}' is present both at top level "
            "and under metrics.relational_gain"
        )

    if top_cycle_found and nested_cycle_found:
        _fail(
            f"ambiguous schema: '{cycle_key}' is present both at top level "
            "and under metrics.relational_gain"
        )

    edge_gains = top_edge_gains if top_edge_found else nested_edge_gains
    cycle_gains = top_cycle_gains if top_cycle_found else nested_cycle_gains

    return edge_gains, cycle_gains


def _read_warn_threshold(payload: dict[str, Any], explicit: float | None) -> float:
    if explicit is not None:
        if not math.isfinite(explicit):
            _fail("--warn-threshold must be finite")
        if explicit < 0:
            _fail("--warn-threshold must be >= 0")
        return float(explicit)

    metrics = payload.get("metrics")
    if isinstance(metrics, dict):
        candidate = metrics.get("relational_gain_warn_threshold")
        if candidate is not None:
            if not _is_finite_number(candidate):
                _fail("metrics.relational_gain_warn_threshold must be a finite number")
            value = float(candidate)
            if value < 0:
                _fail("metrics.relational_gain_warn_threshold must be >= 0")
            return value

        nested = metrics.get("relational_gain")
        if isinstance(nested, dict):
            candidate = nested.get("warn_threshold")
            if candidate is not None:
                if not _is_finite_number(candidate):
                    _fail("metrics.relational_gain.warn_threshold must be a finite number")
                value = float(candidate)
                if value < 0:
                    _fail("metrics.relational_gain.warn_threshold must be >= 0")
                return value

    return DEFAULT_WARN_THRESHOLD


def relational_gain_verdict(
    edge_gains: list[float],
    cycle_gains: list[float],
    warn_threshold: float,
) -> RelationalGainResult:
    max_edge = max(edge_gains) if edge_gains else 0.0
    max_cycle = max(cycle_gains) if cycle_gains else 0.0

    offending_edges = [x for x in edge_gains if x > 1.0]
    offending_cycles = [x for x in cycle_gains if x > 1.0]

    near_boundary_edges = [x for x in edge_gains if warn_threshold <= x <= 1.0]
    near_boundary_cycles = [x for x in cycle_gains if warn_threshold <= x <= 1.0]

    if offending_edges or offending_cycles:
        verdict = "FAIL"
    elif near_boundary_edges or near_boundary_cycles:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return RelationalGainResult(
        verdict=verdict,
        max_edge_gain=max_edge,
        max_cycle_gain=max_cycle,
        warn_threshold=warn_threshold,
        checked_edges=len(edge_gains),
        checked_cycles=len(cycle_gains),
        offending_edges=offending_edges,
        offending_cycles=offending_cycles,
        near_boundary_edges=near_boundary_edges,
        near_boundary_cycles=near_boundary_cycles,
    )


def _build_output(input_path: Path, result: RelationalGainResult) -> dict[str, Any]:
    return {
        "checker_version": CHECKER_VERSION,
        "verdict": result.verdict,
        "input": {
            "path": str(input_path),
        },
        "metrics": {
            "checked_edges": result.checked_edges,
            "checked_cycles": result.checked_cycles,
            "max_edge_gain": result.max_edge_gain,
            "max_cycle_gain": result.max_cycle_gain,
            "warn_threshold": result.warn_threshold,
            "offending_edges": result.offending_edges,
            "offending_cycles": result.offending_cycles,
            "near_boundary_edges": result.near_boundary_edges,
            "near_boundary_cycles": result.near_boundary_cycles,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Shadow-only relational gain checker. "
            "Fails if any edge or cycle gain exceeds 1.0."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input JSON.",
    )
    parser.add_argument(
        "--out",
        help="Optional path to write the output artifact JSON.",
    )
    parser.add_argument(
        "--warn-threshold",
        type=float,
        default=None,
        help="Optional warning threshold override.",
    )
    parser.add_argument(
        "--edge-key",
        default=DEFAULT_EDGE_KEY,
        help=f"Input key for edge gains (default: {DEFAULT_EDGE_KEY}).",
    )
    parser.add_argument(
        "--cycle-key",
        default=DEFAULT_CYCLE_KEY,
        help=f"Input key for cycle gains (default: {DEFAULT_CYCLE_KEY}).",
    )
    parser.add_argument(
        "--require-data",
        action="store_true",
        help="Fail if neither edge nor cycle gain data is present.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    input_path = Path(args.input)
    payload = _load_json(input_path)

    edge_gains, cycle_gains = _extract_gains(
        payload=payload,
        edge_key=args.edge_key,
        cycle_key=args.cycle_key,
    )

    if args.require_data and not edge_gains and not cycle_gains:
        _fail(
            "no relational gain data found; "
            f"expected '{args.edge_key}' and/or '{args.cycle_key}'"
        )

    warn_threshold = _read_warn_threshold(payload, args.warn_threshold)

    result = relational_gain_verdict(
        edge_gains=edge_gains,
        cycle_gains=cycle_gains,
        warn_threshold=warn_threshold,
    )

    output = _build_output(input_path=input_path, result=result)

    if args.out:
        _write_json(Path(args.out), output)

    print(json.dumps(output, indent=2, sort_keys=True))

    return 1 if result.verdict == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
