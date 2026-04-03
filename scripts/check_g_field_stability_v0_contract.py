#!/usr/bin/env python3
"""Contract checker for g_field_stability_v0.json.

Fail-closed goals:
- validate the expected top-level overlay envelope
- validate strict RFC3339 UTC timestamps
- validate numbers/integers/booleans strictly (no bool-as-int loopholes)
- validate only conservative consistency rules already supported by the
  current schema + committed sample shape
- stay stdlib-only

Conservative means:
- enforce summary.num_runs == len(runs) only when `runs` is present
- enforce summary.unstable_gates == sum(g.is_unstable) only when `gates` is present
- do not yet derive summary.g_mean_global / summary.g_std_global /
  summary.max_gate_std / summary.num_points from optional detail arrays
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence


_RFC3339_UTC_Z_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)


def _die(msg: str) -> None:
    print(f"[contract:error] {msg}", file=sys.stderr)
    raise SystemExit(2)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _die(f"Input file not found: {path}")
    except json.JSONDecodeError as exc:
        _die(f"Invalid JSON: {path} ({exc})")

    if not isinstance(data, dict):
        _die(f"Top-level JSON must be an object, got {type(data).__name__}")
    return data


def _require_key(d: Dict[str, Any], key: str) -> Any:
    if key not in d:
        _die(f"Missing required key: {key}")
    return d[key]


def _expect_exact_keys(
    name: str,
    d: Dict[str, Any],
    *,
    allowed: set[str],
    required: set[str],
) -> None:
    extra = sorted(set(d.keys()) - allowed)
    missing = sorted(required - set(d.keys()))
    if extra:
        _die(f"Unexpected key(s) in '{name}': {', '.join(extra)}")
    if missing:
        _die(f"Missing key(s) in '{name}': {', '.join(missing)}")


def _expect_dict(name: str, v: Any) -> Dict[str, Any]:
    if not isinstance(v, dict):
        _die(f"Expected '{name}' to be object, got {type(v).__name__}")
    return v


def _expect_list(name: str, v: Any) -> List[Any]:
    if not isinstance(v, list):
        _die(f"Expected '{name}' to be array, got {type(v).__name__}")
    return v


def _expect_bool(name: str, v: Any) -> bool:
    if not isinstance(v, bool):
        _die(f"Expected '{name}' to be boolean, got {type(v).__name__}")
    return v


def _expect_str(name: str, v: Any) -> str:
    if not isinstance(v, str):
        _die(f"Expected '{name}' to be string, got {type(v).__name__}")
    if not v.strip():
        _die(f"Expected '{name}' to be non-empty string")
    return v


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


def _expect_number_ge0(name: str, v: Any) -> float:
    v_f = _expect_plain_number(name, v)
    if v_f < 0:
        _die(f"Expected '{name}' to be >= 0, got {v_f}")
    return v_f


def _normalize_rfc3339_utc_z_for_fromisoformat(s: str) -> str:
    """Normalize an RFC3339 UTC timestamp for Python's fromisoformat().

    Python's datetime.fromisoformat() rejects fractional seconds longer than
    6 digits, while the contract surface allows any positive fractional
    precision. Keep the original regex as the contract surface, then truncate
    only for parser compatibility.
    """
    if "." not in s:
        return s.replace("Z", "+00:00")

    head, frac_z = s.split(".", 1)
    frac = frac_z[:-1]  # strip trailing Z
    frac = frac[:6]     # Python supports up to microseconds
    return f"{head}.{frac}+00:00"


def _expect_datetime_utc_z(name: str, v: Any) -> None:
    s = _expect_str(name, v)
    if not _RFC3339_UTC_Z_RE.fullmatch(s):
        _die(
            f"Expected '{name}' to be RFC3339 UTC datetime "
            f"(YYYY-MM-DDTHH:MM:SS[.fff]Z), got {s!r}"
        )
    try:
        _dt.datetime.fromisoformat(_normalize_rfc3339_utc_z_for_fromisoformat(s))
    except ValueError as exc:
        _die(f"Expected '{name}' to be RFC3339/ISO-8601 UTC timestamp: {exc}")


def _validate_summary(summary_raw: Any) -> Dict[str, Any]:
    summary = _expect_dict("summary", summary_raw)
    _expect_exact_keys(
        "summary",
        summary,
        allowed={
            "num_runs",
            "num_points",
            "g_mean_global",
            "g_std_global",
            "max_gate_std",
            "unstable_gates",
        },
        required={
            "num_runs",
            "num_points",
            "g_mean_global",
            "g_std_global",
            "max_gate_std",
            "unstable_gates",
        },
    )

    _expect_int_ge0("summary.num_runs", summary["num_runs"])
    _expect_int_ge0("summary.num_points", summary["num_points"])
    _expect_plain_number("summary.g_mean_global", summary["g_mean_global"])
    _expect_number_ge0("summary.g_std_global", summary["g_std_global"])
    _expect_number_ge0("summary.max_gate_std", summary["max_gate_std"])
    _expect_int_ge0("summary.unstable_gates", summary["unstable_gates"])
    return summary


def _validate_runs(runs_raw: Any) -> List[Dict[str, Any]]:
    runs = _expect_list("runs", runs_raw)
    out: List[Dict[str, Any]] = []
    seen_run_ids: set[str] = set()

    for i, item in enumerate(runs):
        name = f"runs[{i}]"
        run = _expect_dict(name, item)
        _expect_exact_keys(
            name,
            run,
            allowed={"run_id", "created_at", "g_mean", "g_std"},
            required={"run_id", "created_at", "g_mean", "g_std"},
        )

        run_id = _expect_str(f"{name}.run_id", _require_key(run, "run_id"))
        if run_id in seen_run_ids:
            _die(f"Duplicate runs[{i}].run_id: {run_id!r}")
        seen_run_ids.add(run_id)

        _expect_datetime_utc_z(
            f"{name}.created_at", _require_key(run, "created_at")
        )
        _expect_plain_number(f"{name}.g_mean", _require_key(run, "g_mean"))
        _expect_number_ge0(f"{name}.g_std", _require_key(run, "g_std"))
        out.append(run)

    return out


def _validate_gates(gates_raw: Any) -> List[Dict[str, Any]]:
    gates = _expect_list("gates", gates_raw)
    out: List[Dict[str, Any]] = []
    seen_gate_ids: set[str] = set()

    for i, item in enumerate(gates):
        name = f"gates[{i}]"
        gate = _expect_dict(name, item)
        _expect_exact_keys(
            name,
            gate,
            allowed={"id", "g_mean", "g_std", "max_delta", "is_unstable"},
            required={"id", "g_mean", "g_std", "max_delta", "is_unstable"},
        )

        gate_id = _expect_str(f"{name}.id", _require_key(gate, "id"))
        if gate_id in seen_gate_ids:
            _die(f"Duplicate gates[{i}].id: {gate_id!r}")
        seen_gate_ids.add(gate_id)

        _expect_plain_number(f"{name}.g_mean", _require_key(gate, "g_mean"))
        _expect_number_ge0(f"{name}.g_std", _require_key(gate, "g_std"))
        _expect_number_ge0(f"{name}.max_delta", _require_key(gate, "max_delta"))
        _expect_bool(f"{name}.is_unstable", _require_key(gate, "is_unstable"))
        out.append(gate)

    return out


def validate(d: Dict[str, Any]) -> None:
    _expect_exact_keys(
        "<root>",
        d,
        allowed={"version", "created_at", "source", "summary", "runs", "gates"},
        required={"version", "created_at", "summary"},
    )

    version = _expect_str("version", _require_key(d, "version"))
    if version != "g_field_stability_v0":
        _die(
            f"Unsupported version: {version!r} "
            "(expected 'g_field_stability_v0')"
        )

    _expect_datetime_utc_z("created_at", _require_key(d, "created_at"))

    if "source" in d:
        _expect_str("source", d["source"])

    summary = _validate_summary(_require_key(d, "summary"))

    runs: Sequence[Dict[str, Any]] | None = None
    if "runs" in d:
        runs = _validate_runs(d["runs"])
        if int(summary["num_runs"]) != len(runs):
            _die(
                "summary.num_runs mismatch: "
                f"expected {len(runs)}, got {summary['num_runs']}"
            )

    gates: Sequence[Dict[str, Any]] | None = None
    if "gates" in d:
        gates = _validate_gates(d["gates"])
        unstable_count = sum(1 for g in gates if bool(g["is_unstable"]))
        if int(summary["unstable_gates"]) != unstable_count:
            _die(
                "summary.unstable_gates mismatch: "
                f"expected {unstable_count}, got {summary['unstable_gates']}"
            )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Contract check: g_field_stability_v0")
    p.add_argument(
        "--in",
        dest="inp",
        default="g_field_stability_v0.json",
        help="Path to g_field_stability_v0.json",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    path = Path(args.inp)
    data = _load_json(path)
    validate(data)
    print(f"OK: contract valid ({path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
