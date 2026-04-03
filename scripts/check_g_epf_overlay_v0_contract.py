#!/usr/bin/env python3
"""Contract checker for g_epf_overlay_v0.json.

Accepts both current overlay shapes:
1. committed demo overlay shape
2. bridge-generated overlay shape

Fail-closed goals:
- validate the top-level envelope
- validate strict RFC3339 UTC timestamps
- validate basic field types and booleans/integers strictly
- validate shape-specific consistency rules
- stay stdlib-only
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set


_RFC3339_UTC_Z_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)


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


def _expect_exact_keys(name: str, d: Dict[str, Any], allowed: Set[str]) -> None:
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
    if not _RFC3339_UTC_Z_RE.fullmatch(s):
        _die(
            f"Expected '{name}' to be RFC3339 UTC datetime "
            f"(YYYY-MM-DDTHH:MM:SS[.fff]Z), got {s!r}"
        )
    try:
        _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        _die(f"Expected '{name}' to be RFC3339/ISO-8601 UTC timestamp: {exc}")


def _validate_string_array(name: str, v: Any) -> List[str]:
    arr = _expect_list(name, v)
    out: List[str] = []
    for i, item in enumerate(arr):
        out.append(_expect_str(f"{name}[{i}]", item))
    return out


def _extract_gate_ids(obj: Any) -> List[str]:
    ids: Set[str] = set()

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("gate_id", "id", "gate") and isinstance(v, str) and v.strip():
                    ids.add(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(obj)
    return sorted(ids)


def _validate_point_like(name: str, point: Any) -> Dict[str, Any]:
    d = _expect_dict(name, point)
    point_id = _expect_str(f"{name}.id", _require_key(d, "id"))
    g_value = _expect_plain_number(f"{name}.g_value", _require_key(d, "g_value"))
    _ = point_id, g_value
    return d


def _validate_demo_panel(idx: int, panel: Any) -> Dict[str, Any]:
    name = f"panels[{idx}]"
    d = _expect_dict(name, panel)

    _expect_str(f"{name}.gate_id", _require_key(d, "gate_id"))
    _expect_str(f"{name}.baseline_decision", _require_key(d, "baseline_decision"))

    if "panel_id" in d:
        _expect_str(f"{name}.panel_id", d["panel_id"])
    if "epf_shadow_decision" in d:
        _expect_str(f"{name}.epf_shadow_decision", d["epf_shadow_decision"])
    if "in_epf_band" in d:
        _expect_bool(f"{name}.in_epf_band", d["in_epf_band"])
    if "distance_to_threshold" in d:
        _expect_number_or_none(f"{name}.distance_to_threshold", d["distance_to_threshold"])
    if "epf_L" in d:
        _expect_number_or_none(f"{name}.epf_L", d["epf_L"])
    if "risk_band" in d:
        _expect_str(f"{name}.risk_band", d["risk_band"])
    if "paradox" in d:
        paradox = _expect_dict(f"{name}.paradox", d["paradox"])
        if "has_paradox" in paradox:
            _expect_bool(f"{name}.paradox.has_paradox", paradox["has_paradox"])
    if "metrics" in d:
        _expect_dict(f"{name}.metrics", d["metrics"])
    if "notes" in d:
        _validate_string_array(f"{name}.notes", d["notes"])

    return d


def _validate_demo_overlay(d: Dict[str, Any]) -> None:
    _expect_exact_keys(
        "<root>",
        d,
        {
            "version",
            "created_at",
            "source",
            "meta",
            "summary",
            "panels",
            "g_field",
            "diagnostics",
        },
    )

    version = _expect_str("version", _require_key(d, "version"))
    if not version.startswith("g_epf_overlay_v0"):
        _die(
            f"Unsupported demo overlay version: {version!r} "
            "(expected prefix 'g_epf_overlay_v0')"
        )

    _expect_datetime_utc_z("created_at", _require_key(d, "created_at"))
    _expect_str("source", _require_key(d, "source"))

    meta = _expect_dict("meta", _require_key(d, "meta"))
    if "generated_at" in meta:
        _expect_datetime_utc_z("meta.generated_at", meta["generated_at"])
    if "overlay_id" in meta:
        _expect_str("meta.overlay_id", meta["overlay_id"])
    if "epf_version" in meta:
        _expect_str("meta.epf_version", meta["epf_version"])
    if "source_run_id" in meta:
        _expect_str("meta.source_run_id", meta["source_run_id"])
    if "source_files" in meta:
        _validate_string_array("meta.source_files", meta["source_files"])

    summary = _expect_dict("summary", _require_key(d, "summary"))
    total_gates = _expect_int_ge0(
        "summary.total_gates", _require_key(summary, "total_gates")
    )
    gates_in_epf_band = _expect_int_ge0(
        "summary.gates_in_epf_band", _require_key(summary, "gates_in_epf_band")
    )
    gates_changed_by_epf = _expect_int_ge0(
        "summary.gates_changed_by_epf", _require_key(summary, "gates_changed_by_epf")
    )
    gates_with_paradox_flag = _expect_int_ge0(
        "summary.gates_with_paradox_flag",
        _require_key(summary, "gates_with_paradox_flag"),
    )
    _expect_bool("summary.shadow_pass", _require_key(summary, "shadow_pass"))
    _validate_string_array("summary.notes", _require_key(summary, "notes"))

    panels = _expect_list("panels", _require_key(d, "panels"))
    validated_panels = [_validate_demo_panel(i, p) for i, p in enumerate(panels)]

    _expect_dict("g_field", _require_key(d, "g_field"))
    _expect_dict("diagnostics", _require_key(d, "diagnostics"))

    computed_total = len(validated_panels)
    computed_in_band = sum(1 for p in validated_panels if p.get("in_epf_band") is True)
    computed_changed = sum(
        1
        for p in validated_panels
        if isinstance(p.get("baseline_decision"), str)
        and isinstance(p.get("epf_shadow_decision"), str)
        and p["baseline_decision"] != p["epf_shadow_decision"]
    )
    computed_paradox = sum(
        1
        for p in validated_panels
        if isinstance(p.get("paradox"), dict)
        and p["paradox"].get("has_paradox") is True
    )

    if total_gates != computed_total:
        _die(
            "summary.total_gates mismatch: "
            f"expected {computed_total}, got {total_gates}"
        )
    if gates_in_epf_band != computed_in_band:
        _die(
            "summary.gates_in_epf_band mismatch: "
            f"expected {computed_in_band}, got {gates_in_epf_band}"
        )
    if gates_changed_by_epf != computed_changed:
        _die(
            "summary.gates_changed_by_epf mismatch: "
            f"expected {computed_changed}, got {gates_changed_by_epf}"
        )
    if gates_with_paradox_flag != computed_paradox:
        _die(
            "summary.gates_with_paradox_flag mismatch: "
            f"expected {computed_paradox}, got {gates_with_paradox_flag}"
        )


def _validate_bridge_overlay(d: Dict[str, Any]) -> None:
    _expect_exact_keys(
        "<root>",
        d,
        {
            "version",
            "created_at",
            "g_field",
            "status_baseline",
            "status_epf",
            "epf_paradox_summary",
            "diagnostics",
        },
    )

    version = _expect_str("version", _require_key(d, "version"))
    if version != "g_epf_overlay_v0":
        _die(
            f"Unsupported bridge overlay version: {version!r} "
            "(expected 'g_epf_overlay_v0')"
        )

    _expect_datetime_utc_z("created_at", _require_key(d, "created_at"))

    g_field = _expect_dict("g_field", _require_key(d, "g_field"))

    status_baseline = _require_key(d, "status_baseline")
    if status_baseline is not None:
        _expect_dict("status_baseline", status_baseline)

    status_epf = _require_key(d, "status_epf")
    if status_epf is not None:
        _expect_dict("status_epf", status_epf)

    epf_paradox_summary = _require_key(d, "epf_paradox_summary")
    if epf_paradox_summary is not None:
        _expect_dict("epf_paradox_summary", epf_paradox_summary)

    diagnostics = _expect_dict("diagnostics", _require_key(d, "diagnostics"))
    _expect_exact_keys(
        "diagnostics",
        diagnostics,
        {"paradox_gate_ids", "g_points_on_paradox_gates"},
    )

    paradox_gate_ids = _validate_string_array(
        "diagnostics.paradox_gate_ids",
        _require_key(diagnostics, "paradox_gate_ids"),
    )
    if len(paradox_gate_ids) != len(set(paradox_gate_ids)):
        _die("diagnostics.paradox_gate_ids must not contain duplicates")

    g_points_on_paradox = _expect_list(
        "diagnostics.g_points_on_paradox_gates",
        _require_key(diagnostics, "g_points_on_paradox_gates"),
    )
    validated_diag_points = [
        _validate_point_like(f"diagnostics.g_points_on_paradox_gates[{i}]", p)
        for i, p in enumerate(g_points_on_paradox)
    ]

    expected_gate_ids = (
        _extract_gate_ids(epf_paradox_summary) if epf_paradox_summary is not None else []
    )
    if paradox_gate_ids != expected_gate_ids:
        _die(
            "diagnostics.paradox_gate_ids mismatch: "
            f"expected {expected_gate_ids}, got {paradox_gate_ids}"
        )

    g_field_points_raw = g_field.get("points", [])
    if not isinstance(g_field_points_raw, list):
        _die("g_field.points must be an array when present")

    validated_g_field_points = [
        _validate_point_like(f"g_field.points[{i}]", p)
        for i, p in enumerate(g_field_points_raw)
    ]

    ids_set = set(expected_gate_ids)
    expected_diag_points = [
        p for p in validated_g_field_points if str(p.get("id", "")) in ids_set
    ]

    if validated_diag_points != expected_diag_points:
        _die(
            "diagnostics.g_points_on_paradox_gates mismatch: "
            f"expected {expected_diag_points}, got {validated_diag_points}"
        )


def validate(d: Dict[str, Any]) -> None:
    if {"source", "meta", "summary", "panels"}.issubset(d.keys()):
        _validate_demo_overlay(d)
        return

    if {"status_baseline", "status_epf", "epf_paradox_summary"}.issubset(d.keys()):
        _validate_bridge_overlay(d)
        return

    _die(
        "Unrecognized g_epf_overlay_v0 shape. "
        "Expected either demo overlay keys "
        "('source','meta','summary','panels',...) or bridge overlay keys "
        "('status_baseline','status_epf','epf_paradox_summary',...)."
    )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Contract check: g_epf_overlay_v0")
    p.add_argument(
        "--in",
        dest="inp",
        default="PULSE_safe_pack_v0/artifacts/g_epf_overlay_v0.json",
        help="Path to g_epf_overlay_v0.json",
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
