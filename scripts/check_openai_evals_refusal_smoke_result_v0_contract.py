#!/usr/bin/env python3
"""
Contract checker for openai_evals_v0/refusal_smoke_result.json.

Fail-closed goals:
- Validate required keys exist (including 'status').
- Validate types and basic invariants.
- Catch regressions where producers drop fields or change shapes.

This checker is intentionally stdlib-only.
"""

from __future__ import annotations

import argparse
import json
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


def _expect_type(name: str, v: Any, t: Any) -> None:
    if not isinstance(v, t):
        _die(f"Expected '{name}' to be {t}, got {type(v).__name__}")


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


def _expect_bool(name: str, v: Any) -> None:
    if not isinstance(v, bool):
        _die(f"Expected '{name}' to be boolean, got {type(v).__name__}")


def _expect_int_ge0(name: str, v: Any) -> None:
    if not isinstance(v, int):
        _die(f"Expected '{name}' to be int, got {type(v).__name__}")
    if v < 0:
        _die(f"Expected '{name}' to be >= 0, got {v}")


def _expect_number_0_1(name: str, v: Any) -> None:
    if not isinstance(v, (int, float)):
        _die(f"Expected '{name}' to be number, got {type(v).__name__}")
    fv = float(v)
    if not (0.0 <= fv <= 1.0):
        _die(f"Expected '{name}' in [0,1], got {fv}")


def validate(d: Dict[str, Any]) -> None:
    # Required top-level fields
    dry_run = _require_key(d, "dry_run")
    _expect_bool("dry_run", dry_run)

    timestamp_utc = _require_key(d, "timestamp_utc")
    _expect_str("timestamp_utc", timestamp_utc)

    dataset = _require_key(d, "dataset")
    _expect_str("dataset", dataset)

    model = _require_key(d, "model")
    _expect_str("model", model)

    file_id = _require_key(d, "file_id")
    _expect_str("file_id", file_id)

    eval_id = _require_key(d, "eval_id")
    _expect_str("eval_id", eval_id)

    run_id = _require_key(d, "run_id")
    _expect_str("run_id", run_id)

    # report_url can be null or string
    report_url = _require_key(d, "report_url")
    _expect_str_or_none("report_url", report_url)

    # ✅ IMPORTANT: status is REQUIRED (key must exist) but may be string|null
    status = _require_key(d, "status")
    _expect_str_or_none("status", status)
    status_s = (status or "").strip()

    result_counts = _require_key(d, "result_counts")
    if not isinstance(result_counts, dict):
        _die(f"Expected 'result_counts' to be object, got {type(result_counts).__name__}")

    total = _require_key(result_counts, "total")
    passed = _require_key(result_counts, "passed")
    failed = _require_key(result_counts, "failed")
    errored = _require_key(result_counts, "errored")

    _expect_int_ge0("result_counts.total", total)
    _expect_int_ge0("result_counts.passed", passed)
    _expect_int_ge0("result_counts.failed", failed)
    _expect_int_ge0("result_counts.errored", errored)

    # Allow future expansion (e.g. skipped) by requiring totals be >= sum of known buckets.
    if passed + failed + errored > total:
        _die(
            "Invalid result_counts: passed+failed+errored exceeds total "
            f"({passed}+{failed}+{errored} > {total})"
        )

    fail_rate = _require_key(d, "fail_rate")
    _expect_number_0_1("fail_rate", fail_rate)

    gate_key = _require_key(d, "gate_key")
    _expect_str("gate_key", gate_key)

    gate_pass = _require_key(d, "gate_pass")
    _expect_bool("gate_pass", gate_pass)

    # -------------------------
    # Fail-closed semantic invariants
    # -------------------------

    # If status is missing/unknown (null/empty), gate_pass must not be True.
    if (status is None) or (status_s == ""):
        if gate_pass:
            _die("gate_pass cannot be true when status is null/empty (fail-closed).")

    # If gate_pass is true, status must be a successful terminal state.
    if gate_pass and status_s not in ("completed", "succeeded"):
        _die("gate_pass=true requires status in {completed,succeeded}.")

    # If dataset is empty (total==0), must fail closed.
    if total == 0 and gate_pass:
        _die("gate_pass cannot be true when result_counts.total == 0 (fail-closed).")

    # If any failures/errors exist, must fail.
    if (failed > 0 or errored > 0) and gate_pass:
        _die("gate_pass cannot be true when failed>0 or errored>0.")

    # Optional: sanity check fail_rate vs failed/total if total>0 (tolerant).
    if total > 0:
        expected = failed / float(total)
        if abs(float(fail_rate) - expected) > 1e-6:
            _die(
                f"fail_rate mismatch: expected failed/total={expected:.9f}, got {float(fail_rate):.9f}"
            )
    else:
        # In your producer you set fail_rate=1.0 for total==0; enforce that here.
        if abs(float(fail_rate) - 1.0) > 1e-9:
            _die(f"fail_rate must be 1.0 when total==0 (fail-closed), got {float(fail_rate)}")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Contract check: OpenAI evals refusal smoke result v0")
    p.add_argument(
        "--in",
        dest="inp",
        default="openai_evals_v0/refusal_smoke_result.json",
        help="Path to refusal_smoke_result.json",
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
