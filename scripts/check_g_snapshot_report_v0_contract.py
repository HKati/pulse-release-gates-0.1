#!/usr/bin/env python3
"""Contract checker for g_snapshot_report_v0 JSON reports.

Fail-closed goals:
- validate the expected top-level report envelope
- validate strict RFC3339 UTC timestamps
- validate that `sources` reflects actual overlay presence
- validate that summary sections match the current source overlays
- stay stdlib-only

This checker targets the JSON output of:

    python scripts/g_snapshot_report.py --root . --format json
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


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
        _die(f"Top-level JSON must be an object: {path}")
    return data


def _load_json_candidates(candidates: Sequence[Path]) -> Optional[Dict[str, Any]]:
    for p in candidates:
        if p.is_file():
            return _load_json(p)
    return None


def _expect_exact_keys(name: str, d: Dict[str, Any], allowed: set[str]) -> None:
    extra = sorted(set(d.keys()) - allowed)
    missing = sorted(allowed - set(d.keys()))
    if extra:
        _die(f"Unexpected key(s) in '{name}': {', '.join(extra)}")
    if missing:
        _die(f"Missing key(s) in '{name}': {', '.join(missing)}")


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


def _float_equal(
    a: float,
    b: float,
    *,
    rel_tol: float = 1e-12,
    abs_tol: float = 1e-12,
) -> bool:
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


def _normalize_ranked_counter_entries(name: str, value: Any) -> List[List[Any]]:
    if not isinstance(value, list):
        _die(f"Expected '{name}' to be array, got {type(value).__name__}")

    out: List[List[Any]] = []
    for i, item in enumerate(value):
        if not isinstance(item, list):
            _die(f"Expected '{name}[{i}]' to be array, got {type(item).__name__}")
        if len(item) != 2:
            _die(f"Expected '{name}[{i}]' to have length 2, got {len(item)}")
        label = _expect_str(f"{name}[{i}][0]", item[0])
        count = _expect_int_ge0(f"{name}[{i}][1]", item[1])
        out.append([label, count])
    return out


def _top_k_counter_map(d: Dict[str, Any], *, k: int = 3) -> List[List[Any]]:
    items: List[tuple[str, int]] = []
    for key, val in d.items():
        if isinstance(key, str) and key and isinstance(val, int) and not isinstance(val, bool):
            items.append((key, val))
    items.sort(key=lambda x: x[1], reverse=True)
    return [[k_, v_] for k_, v_ in items[:k]]


def _summarize_g_field(obj: Dict[str, Any]) -> Dict[str, Any]:
    summary = obj.get("summary") or {}
    points = obj.get("points") or []
    g_values: List[float] = []

    if isinstance(points, list):
        for i, p in enumerate(points):
            if not isinstance(p, dict):
                _die(f"Expected g_field.points[{i}] to be object")
            gv = p.get("g_value")
            if isinstance(gv, (int, float)) and not isinstance(gv, bool):
                g_values.append(float(gv))

    out: Dict[str, Any] = {
        "num_points": summary.get("num_points", len(points) if isinstance(points, list) else 0),
        "g_mean": summary.get("g_mean"),
        "g_std": summary.get("g_std"),
    }
    if g_values:
        out["g_min"] = min(g_values)
        out["g_max"] = max(g_values)
    else:
        out["g_min"] = None
        out["g_max"] = None
    return out


def _summarize_g_epf(obj: Dict[str, Any]) -> Dict[str, Any]:
    diagnostics = obj.get("diagnostics") or {}
    paradox_gate_ids = diagnostics.get("paradox_gate_ids") or []
    points = diagnostics.get("g_points_on_paradox_gates") or []

    gate_set = {
        g for g in paradox_gate_ids if isinstance(g, str) and g
    }

    g_values: List[float] = []
    if isinstance(points, list):
        for i, p in enumerate(points):
            if not isinstance(p, dict):
                _die(f"Expected g_epf diagnostics point[{i}] to be object")
            gv = p.get("g_value")
            if isinstance(gv, (int, float)) and not isinstance(gv, bool):
                g_values.append(float(gv))

    out: Dict[str, Any] = {
        "num_paradox_gates": len(gate_set),
        "num_g_points_on_paradox_gates": len(points) if isinstance(points, list) else 0,
    }
    if g_values:
        out["g_on_paradox_min"] = min(g_values)
        out["g_on_paradox_max"] = max(g_values)
    else:
        out["g_on_paradox_min"] = None
        out["g_on_paradox_max"] = None
    return out


def _summarize_gpt_external(obj: Dict[str, Any]) -> Dict[str, Any]:
    summary = obj.get("summary") or {}
    vendors = summary.get("vendors") or {}
    models = summary.get("models") or {}

    return {
        "total_records": summary.get("total_records", 0),
        "num_external_gpt": summary.get("num_external_gpt", 0),
        "num_internal": summary.get("num_internal", 0),
        "num_unknown": summary.get("num_unknown", 0),
        "top_vendors": _top_k_counter_map(vendors),
        "top_models": _top_k_counter_map(models),
    }


def _summarize_g_stability(obj: Dict[str, Any]) -> Dict[str, Any]:
    summary = obj.get("summary") or {}
    if not isinstance(summary, dict):
        _die("Expected g_field_stability.summary to be object when present")
    return summary


def _build_expected_sections(root: Path) -> Dict[str, Any]:
    def rp(*parts: str) -> Path:
        return root.joinpath(*parts)

    g_field = _load_json_candidates(
        [
            rp("PULSE_safe_pack_v0", "artifacts", "g_field_v0.json"),
            rp("g_field_v0.json"),
        ]
    )
    g_stab = _load_json_candidates(
        [
            rp("PULSE_safe_pack_v0", "artifacts", "g_field_stability_v0.json"),
            rp("g_field_stability_v0.json"),
        ]
    )
    g_epf = _load_json_candidates(
        [
            rp("PULSE_safe_pack_v0", "artifacts", "g_epf_overlay_v0.json"),
            rp("g_epf_overlay_v0.json"),
        ]
    )
    gpt_ext = _load_json_candidates(
        [
            rp("PULSE_safe_pack_v0", "artifacts", "gpt_external_detection_v0.json"),
            rp("gpt_external_detection_v0.json"),
        ]
    )

    return {
        "sources": {
            "g_field_v0": g_field is not None,
            "g_field_stability_v0": g_stab is not None,
            "g_epf_overlay_v0": g_epf is not None,
            "gpt_external_detection_v0": gpt_ext is not None,
        },
        "g_field": _summarize_g_field(g_field) if g_field else None,
        "g_field_stability": _summarize_g_stability(g_stab) if g_stab else None,
        "g_epf": _summarize_g_epf(g_epf) if g_epf else None,
        "gpt_external": _summarize_gpt_external(gpt_ext) if gpt_ext else None,
    }


def _validate_sources(actual: Any, expected: Dict[str, bool]) -> None:
    if not isinstance(actual, dict):
        _die(f"Expected 'sources' to be object, got {type(actual).__name__}")
    _expect_exact_keys("sources", actual, set(expected.keys()))
    for key, expected_val in expected.items():
        actual_val = _expect_bool(f"sources.{key}", actual[key])
        if actual_val != expected_val:
            _die(
                f"sources.{key} mismatch: expected {expected_val}, got {actual_val}"
            )


def _validate_g_field_section(actual: Any, expected: Any) -> None:
    if expected is None:
        if actual is not None:
            _die("Expected 'g_field' to be null because source overlay is missing")
        return

    if not isinstance(actual, dict):
        _die(f"Expected 'g_field' to be object|null, got {type(actual).__name__}")

    _expect_exact_keys(
        "g_field",
        actual,
        {"num_points", "g_mean", "g_std", "g_min", "g_max"},
    )

    num_points = _expect_int_ge0("g_field.num_points", actual["num_points"])
    g_mean = _expect_number_or_none("g_field.g_mean", actual["g_mean"])
    g_std = _expect_number_or_none("g_field.g_std", actual["g_std"])
    g_min = _expect_number_or_none("g_field.g_min", actual["g_min"])
    g_max = _expect_number_or_none("g_field.g_max", actual["g_max"])

    if g_std is not None and g_std < 0:
        _die(f"Expected 'g_field.g_std' to be >= 0, got {g_std}")

    if num_points != expected["num_points"]:
        _die(
            f"g_field.num_points mismatch: expected {expected['num_points']}, got {num_points}"
        )

    for key, actual_v, expected_v in (
        ("g_mean", g_mean, expected["g_mean"]),
        ("g_std", g_std, expected["g_std"]),
        ("g_min", g_min, expected["g_min"]),
        ("g_max", g_max, expected["g_max"]),
    ):
        if actual_v is None and expected_v is None:
            continue
        if actual_v is None or expected_v is None:
            _die(f"g_field.{key} mismatch: expected {expected_v}, got {actual_v}")
        if not _float_equal(float(actual_v), float(expected_v)):
            _die(f"g_field.{key} mismatch: expected {expected_v}, got {actual_v}")


def _validate_g_field_stability_section(actual: Any, expected: Any) -> None:
    if expected is None:
        if actual is not None:
            _die(
                "Expected 'g_field_stability' to be null because source overlay is missing"
            )
        return

    if not isinstance(actual, dict):
        _die(
            f"Expected 'g_field_stability' to be object|null, got {type(actual).__name__}"
        )

    if actual != expected:
        _die(
            f"g_field_stability mismatch: expected {expected!r}, got {actual!r}"
        )


def _validate_g_epf_section(actual: Any, expected: Any) -> None:
    if expected is None:
        if actual is not None:
            _die("Expected 'g_epf' to be null because source overlay is missing")
        return

    if not isinstance(actual, dict):
        _die(f"Expected 'g_epf' to be object|null, got {type(actual).__name__}")

    _expect_exact_keys(
        "g_epf",
        actual,
        {
            "num_paradox_gates",
            "num_g_points_on_paradox_gates",
            "g_on_paradox_min",
            "g_on_paradox_max",
        },
    )

    num_paradox_gates = _expect_int_ge0(
        "g_epf.num_paradox_gates", actual["num_paradox_gates"]
    )
    num_points = _expect_int_ge0(
        "g_epf.num_g_points_on_paradox_gates", actual["num_g_points_on_paradox_gates"]
    )
    g_min = _expect_number_or_none("g_epf.g_on_paradox_min", actual["g_on_paradox_min"])
    g_max = _expect_number_or_none("g_epf.g_on_paradox_max", actual["g_on_paradox_max"])

    if num_paradox_gates != expected["num_paradox_gates"]:
        _die(
            "g_epf.num_paradox_gates mismatch: "
            f"expected {expected['num_paradox_gates']}, got {num_paradox_gates}"
        )
    if num_points != expected["num_g_points_on_paradox_gates"]:
        _die(
            "g_epf.num_g_points_on_paradox_gates mismatch: "
            f"expected {expected['num_g_points_on_paradox_gates']}, got {num_points}"
        )

    for key, actual_v, expected_v in (
        ("g_on_paradox_min", g_min, expected["g_on_paradox_min"]),
        ("g_on_paradox_max", g_max, expected["g_on_paradox_max"]),
    ):
        if actual_v is None and expected_v is None:
            continue
        if actual_v is None or expected_v is None:
            _die(f"g_epf.{key} mismatch: expected {expected_v}, got {actual_v}")
        if not _float_equal(float(actual_v), float(expected_v)):
            _die(f"g_epf.{key} mismatch: expected {expected_v}, got {actual_v}")


def _validate_gpt_external_section(actual: Any, expected: Any) -> None:
    if expected is None:
        if actual is not None:
            _die("Expected 'gpt_external' to be null because source overlay is missing")
        return

    if not isinstance(actual, dict):
        _die(
            f"Expected 'gpt_external' to be object|null, got {type(actual).__name__}"
        )

    _expect_exact_keys(
        "gpt_external",
        actual,
        {
            "total_records",
            "num_external_gpt",
            "num_internal",
            "num_unknown",
            "top_vendors",
            "top_models",
        },
    )

    for key in (
        "total_records",
        "num_external_gpt",
        "num_internal",
        "num_unknown",
    ):
        actual_v = _expect_int_ge0(f"gpt_external.{key}", actual[key])
        if actual_v != expected[key]:
            _die(
                f"gpt_external.{key} mismatch: expected {expected[key]}, got {actual_v}"
            )

    actual_top_vendors = _normalize_ranked_counter_entries(
        "gpt_external.top_vendors", actual["top_vendors"]
    )
    actual_top_models = _normalize_ranked_counter_entries(
        "gpt_external.top_models", actual["top_models"]
    )

    if actual_top_vendors != expected["top_vendors"]:
        _die(
            "gpt_external.top_vendors mismatch: "
            f"expected {expected['top_vendors']}, got {actual_top_vendors}"
        )
    if actual_top_models != expected["top_models"]:
        _die(
            "gpt_external.top_models mismatch: "
            f"expected {expected['top_models']}, got {actual_top_models}"
        )


def validate(report: Dict[str, Any], *, root: Path) -> None:
    _expect_exact_keys(
        "<root>",
        report,
        {
            "version",
            "generated_at",
            "sources",
            "g_field",
            "g_field_stability",
            "g_epf",
            "gpt_external",
        },
    )

    version = _expect_str("version", report["version"])
    if version != "g_snapshot_report_v0":
        _die(
            f"Unsupported report version: {version!r} "
            "(expected 'g_snapshot_report_v0')"
        )

    _expect_datetime_utc_z("generated_at", report["generated_at"])

    expected = _build_expected_sections(root)

    _validate_sources(report["sources"], expected["sources"])
    _validate_g_field_section(report["g_field"], expected["g_field"])
    _validate_g_field_stability_section(
        report["g_field_stability"], expected["g_field_stability"]
    )
    _validate_g_epf_section(report["g_epf"], expected["g_epf"])
    _validate_gpt_external_section(report["gpt_external"], expected["gpt_external"])


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Contract check: g_snapshot_report_v0 (JSON)"
    )
    p.add_argument(
        "--in",
        dest="inp",
        default="PULSE_safe_pack_v0/artifacts/g_snapshot_report_v0.json",
        help="Path to g_snapshot_report_v0 JSON report",
    )
    p.add_argument(
        "--root",
        default=".",
        help="Repo root used to recompute expected source-derived sections",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    report_path = Path(args.inp)
    root = Path(args.root).resolve()

    report = _load_json(report_path)
    validate(report, root=root)

    print(f"OK: contract valid ({report_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
