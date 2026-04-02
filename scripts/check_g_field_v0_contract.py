#!/usr/bin/env python3
"""Contract checker for g_field_v0.json.

Fail-closed goals:
- validate the expected top-level overlay envelope
- validate summary/points field types
- validate that summary values match the concrete point list
- stay stdlib-only
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List


def _die(msg: str) -> None:
    print(f"[contract:error] {msg}", file=sys.stderr)
    raise SystemExit(2)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _die(f"Input file not found: {path}")
    except json.JSONDecodeError as exc:
        _die(f"Invalid JSON: {path} ({exc})")
    return {}  # unreachable


def _require_key(d: Dict[str, Any], key: str) -> Any:
    if key not in d:
        _die(f"Missing required key: {key}")
    return d[key]


def _expect_exact_keys(name: str, d: Dict[str, Any], allowed: set[str]) -> None:
    extra = sorted(set(d.keys()) - allowed)
    if extra:
        _die(f"Unexpected key(s) in '{name}': {', '.join(extra)}")


def _expect_dict(name: str, v: Any) -> Dict[str, Any]:
    if not isinstance(v, dict):
        _die(f"Expected '{name}' to be object, got {type(v).__name__}")
    return v


def _expect_list(name: str, v: Any) -> List[Any]:
    if not isinstance(v, list):
        _die(f"Expected '{name}' to be array, got {type(v).__name__}")
    return v


def _expect_str(name: str, v: Any) -> str:
    if not isinstance(v, str):
        _die(f"Expected '{name}' to be string, got {type(v).__name__}")
    if not v.strip():
        _die(f"Expected '{name}' to be non-empty string")
    return v


def _expect_str_or_none(name: str, v: Any) -> str | None:
    if v is None:
        return None
    return _expect_str(name, v)


def _expect_plain_int(name: str, v: Any) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        _die(f"Expected '{name}' to be int, got {type(v).__name__}")
    return v


def _expect_int_ge0(name: str, v: Any) -> int:
    v_i = _expect_plain_int(name, v)
    if v_i < 0:
        _die(f"Expected '{name}' to be >= 0, got {v_i}")
    return v_i


def _expect_plain_number(name: str, v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        _die(f"Expected '{name}' to be number, got {type(v).__name__}")
    v_f = float(v)
    if not math.isfinite(v_f):
        _die(f"Expected '{name}' to be finite number, got {v!r}")
    return v_f


def _expect_number_or_none(name: str, v: Any) -> float | None:
    if v is None:
        return None
    return _expect_plain_number(name, v)


def _expect_datetime_utc_z(name: str, v: Any) -> None:
    s = _expect_str(name, v)
    if not s.endswith("Z"):
        _die(f"Expected '{name}' to end with 'Z', got {s!r}")
    try:
        _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        _die(f"Expected '{name}' to be RFC3339/ISO-8601 UTC timestamp: {exc}")


def _float_equal(a: float, b: float, *, rel_tol: float = 1e-12, abs_tol: float = 1e-12) -> bool:
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


def _validate_point(list_idx: int, point: Any) -> Dict[str, Any]:
    name = f"points[{list_idx}]"
    d = _expect_dict(name, point)
    _expect_exact_keys(name, d, {"id", "g_value"})

    point_id = _require_key(d, "id")
    _expect_str(f"{name}.id", point_id)

    g_value = _require_key(d, "g_value")
    _expect_plain_number(f"{name}.g_value", g_value)

    return d


def validate(d: Dict[str, Any]) -> None:
    _expect_exact_keys(
        "<root>",
        d,
        {"version", "source", "created_at", "run_id", "summary", "points"},
    )

    version = _expect_str("version", _require_key(d, "version"))
    if version != "g_field_v0":
        _die(f"Unsupported version: {version!r} (expected 'g_field_v0')")

    source = _expect_str("source", _require_key(d, "source"))
    if source != "internal_hpc_g_child":
        _die(
            f"Unsupported source: {source!r} "
            "(expected 'internal_hpc_g_child')"
        )

    _expect_datetime_utc_z("created_at", _require_key(d, "created_at"))
    _expect_str_or_none("run_id", _require_key(d, "run_id"))

    summary_raw = _require_key(d, "summary")
    summary = _expect_dict("summary", summary_raw)
    _expect_exact_keys("summary", summary, {"num_points", "g_mean", "g_std"})

    num_points = _expect_int_ge0(
        "summary.num_points",
        _require_key(summary, "num_points"),
    )
    g_mean = _expect_number_or_none(
        "summary.g_mean",
        _require_key(summary, "g_mean"),
    )
    g_std = _expect_number_or_none(
        "summary.g_std",
        _require_key(summary, "g_std"),
    )
    if g_std is not None and g_std < 0:
        _die(f"Expected 'summary.g_std' to be >= 0, got {g_std}")

    points_raw = _require_key(d, "points")
    points = _expect_list("points", points_raw)
    validated_points = [_validate_point(i, p) for i, p in enumerate(points)]

    values = [float(p["g_value"]) for p in validated_points]
    computed_num_points = len(values)

    if num_points != computed_num_points:
        _die(
            "summary.num_points mismatch: "
            f"expected {computed_num_points}, got {num_points}"
        )

    if computed_num_points == 0:
        if g_mean is not None:
            _die("summary.g_mean must be null when points is empty")
        if g_std is not None:
            _die("summary.g_std must be null when points is empty")
        return

    computed_mean = statistics.fmean(values)
    computed_std = statistics.pstdev(values) if computed_num_points > 1 else 0.0

    if g_mean is None:
        _die("summary.g_mean must be numeric when points is non-empty")
    if g_std is None:
        _die("summary.g_std must be numeric when points is non-empty")

    if not _float_equal(g_mean, computed_mean):
        _die(
            "summary.g_mean mismatch: "
            f"expected {computed_mean}, got {g_mean}"
        )

    if not _float_equal(g_std, computed_std):
        _die(
            "summary.g_std mismatch: "
            f"expected {computed_std}, got {g_std}"
        )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Contract check: g_field_v0")
    p.add_argument(
        "--in",
        dest="inp",
        default="PULSE_safe_pack_v0/artifacts/g_field_v0.json",
        help="Path to g_field_v0.json",
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
