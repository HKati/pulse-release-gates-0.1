#!/usr/bin/env python3
"""Contract checker for gpt_external_detection_v0.json.

Fail-closed goals:
- validate required top-level keys exist
- validate record field types and basic invariants
- validate summary consistency against the concrete record list
- stay stdlib-only
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


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


def _expect_dict(name: str, v: Any) -> Dict[str, Any]:
    if not isinstance(v, dict):
        _die(f"Expected '{name}' to be object, got {type(v).__name__}")
    return v


def _expect_list(name: str, v: Any) -> List[Any]:
    if not isinstance(v, list):
        _die(f"Expected '{name}' to be array, got {type(v).__name__}")
    return v


def _expect_bool(name: str, v: Any) -> None:
    if not isinstance(v, bool):
        _die(f"Expected '{name}' to be boolean, got {type(v).__name__}")


def _expect_plain_int(name: str, v: Any) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        _die(f"Expected '{name}' to be int, got {type(v).__name__}")
    return v

def _expect_int_ge0(name: str, v: Any) -> int:
    v_i = _expect_plain_int(name, v)
    if v_i < 0:
        _die(f"Expected '{name}' to be >= 0, got {v_i}")
    return v_i

def _expect_int_ge1(name: str, v: Any) -> int:
      v_i = _expect_plain_int(name, v)
    if v_i < 1:
        _die(f"Expected '{name}' to be >= 1, got {v_i}")
    return v_i


def _expect_str(name: str, v: Any) -> str:
    if not isinstance(v, str):
        _die(f"Expected '{name}' to be string, got {type(v).__name__}")
    if not v.strip():
        _die(f"Expected '{name}' to be non-empty string")
    return v


def _expect_str_or_none(name: str, v: Any) -> str | None:
    if v is None:
        return None
    if not isinstance(v, str):
        _die(f"Expected '{name}' to be string|null, got {type(v).__name__}")
    if not v.strip():
        _die(f"Expected '{name}' to be non-empty string when present")
    return v


def _expect_counter_map(name: str, v: Any) -> Dict[str, int]:
    d = _expect_dict(name, v)
    out: Dict[str, int] = {}
    for k, val in d.items():
        if not isinstance(k, str) or not k.strip():
            _die(f"Expected all keys in '{name}' to be non-empty strings")
              val_i = _expect_plain_int(f"{name}[{k}]", val)
        if val_i < 0:
            _die(f"Expected '{name}[{k}]' to be >= 0, got {val_i}")
        out[k] = val_i
    return out


def _expect_datetime_utc_z(name: str, v: Any) -> None:
    s = _expect_str(name, v)
    if not s.endswith("Z"):
        _die(f"Expected '{name}' to end with 'Z', got {s!r}")
    try:
        _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        _die(f"Expected '{name}' to be RFC3339/ISO-8601 UTC timestamp: {exc}")


def _normalize_counter_key(value: str | None) -> str | None:
    if value is None:
        return None
    s = value.strip().lower()
    return s or None


def _validate_record(idx: int, rec: Any, seen_idxs: set[int]) -> Dict[str, Any]:
    name = f"records[{idx}]"
    d = _expect_dict(name, rec)

    rec_idx = _require_key(d, "idx")
    rec_idx_i = _expect_int_ge1(f"{name}.idx", rec_idx)
    if rec_idx_i in seen_idxs:
        _die(f"Duplicate record idx detected: {rec_idx_i}")
    seen_idxs.add(rec_idx_i)

    rec_id = _require_key(d, "id")
    _expect_str_or_none(f"{name}.id", rec_id)

    is_external_gpt = _require_key(d, "is_external_gpt")
    _expect_bool(f"{name}.is_external_gpt", is_external_gpt)

    is_internal = _require_key(d, "is_internal")
    _expect_bool(f"{name}.is_internal", is_internal)

    vendor = _require_key(d, "vendor")
    _expect_str_or_none(f"{name}.vendor", vendor)

    model = _require_key(d, "model")
    _expect_str_or_none(f"{name}.model", model)

    reason = _require_key(d, "reason")
    _expect_str(f"{name}.reason", reason)

    if is_external_gpt and is_internal:
        _die(
            f"{name} cannot be both external_gpt=true and internal=true "
            "(internal markers should win outright)"
        )

    return d


def validate(d: Dict[str, Any]) -> None:
    version = _require_key(d, "version")
    version_s = _expect_str("version", version)
    if version_s != "gpt_external_detection_v0":
        _die(
            f"Unsupported version: {version_s!r} "
            "(expected 'gpt_external_detection_v0')"
        )

    created_at = _require_key(d, "created_at")
    _expect_datetime_utc_z("created_at", created_at)

    input_file = _require_key(d, "input_file")
    _expect_str("input_file", input_file)

    summary_raw = _require_key(d, "summary")
    summary = _expect_dict("summary", summary_raw)

    total_records = _expect_int_ge0(
        "summary.total_records", _require_key(summary, "total_records")
    )
    num_external_gpt = _expect_int_ge0(
        "summary.num_external_gpt", _require_key(summary, "num_external_gpt")
    )
    num_internal = _expect_int_ge0(
        "summary.num_internal", _require_key(summary, "num_internal")
    )
    num_unknown = _expect_int_ge0(
        "summary.num_unknown", _require_key(summary, "num_unknown")
    )
    vendors = _expect_counter_map("summary.vendors", _require_key(summary, "vendors"))
    models = _expect_counter_map("summary.models", _require_key(summary, "models"))

    records_raw = _require_key(d, "records")
    records = _expect_list("records", records_raw)

    seen_idxs: set[int] = set()
    validated_records = [
        _validate_record(i, rec, seen_idxs) for i, rec in enumerate(records)
    ]

    computed_total = len(validated_records)
    computed_external = 0
    computed_internal = 0
    computed_vendors: Dict[str, int] = {}
    computed_models: Dict[str, int] = {}

    for rec in validated_records:
        if rec["is_external_gpt"] is True:
            computed_external += 1
        if rec["is_internal"] is True:
            computed_internal += 1

        vendor_key = _normalize_counter_key(rec.get("vendor"))
        if vendor_key is not None:
            computed_vendors[vendor_key] = computed_vendors.get(vendor_key, 0) + 1

        model_key = _normalize_counter_key(rec.get("model"))
        if model_key is not None:
            computed_models[model_key] = computed_models.get(model_key, 0) + 1

    computed_unknown = computed_total - computed_external - computed_internal
    if computed_unknown < 0:
        _die(
            "Computed num_unknown < 0 "
            "(external/internal classification overlap is inconsistent)"
        )

    if total_records != computed_total:
        _die(
            "summary.total_records mismatch: "
            f"expected {computed_total}, got {total_records}"
        )

    if num_external_gpt != computed_external:
        _die(
            "summary.num_external_gpt mismatch: "
            f"expected {computed_external}, got {num_external_gpt}"
        )

    if num_internal != computed_internal:
        _die(
            "summary.num_internal mismatch: "
            f"expected {computed_internal}, got {num_internal}"
        )

    if num_unknown != computed_unknown:
        _die(
            "summary.num_unknown mismatch: "
            f"expected {computed_unknown}, got {num_unknown}"
        )

    if num_external_gpt + num_internal + num_unknown != total_records:
        _die(
            "summary counts inconsistent: "
            "num_external_gpt + num_internal + num_unknown must equal total_records"
        )

    if vendors != computed_vendors:
        _die(
            "summary.vendors mismatch: "
            f"expected {computed_vendors}, got {vendors}"
        )

    if models != computed_models:
        _die(
            "summary.models mismatch: "
            f"expected {computed_models}, got {models}"
        )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Contract check: gpt_external_detection_v0"
    )
    p.add_argument(
        "--in",
        dest="inp",
        default="PULSE_safe_pack_v0/artifacts/gpt_external_detection_v0.json",
        help="Path to gpt_external_detection_v0.json",
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
