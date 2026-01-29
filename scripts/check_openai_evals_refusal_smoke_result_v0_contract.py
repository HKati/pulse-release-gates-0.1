#!/usr/bin/env python3
"""
Fail-closed contract check for openai_evals_v0/refusal_smoke_result.json.

Stdlib-only on purpose.
Validates:
- required keys + types
- result_counts sanity
- fail_rate consistency
- gate_pass matches documented fail-closed semantics
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


OK_STATUSES = {"completed", "succeeded"}


def _err(msg: str) -> None:
    print(f"::error::{msg}", file=sys.stderr)


def _die(msg: str, code: int = 1) -> None:
    _err(msg)
    raise SystemExit(code)


def _read_json(p: Path) -> Dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        _die(f"Invalid JSON: {p} ({e})")


def _as_int(x: Any, key: str) -> int:
    if isinstance(x, bool) or not isinstance(x, int):
        _die(f"Expected integer for '{key}', got {type(x).__name__}")
    if x < 0:
        _die(f"'{key}' must be >= 0, got {x}")
    return x


def _as_bool(x: Any, key: str) -> bool:
    if not isinstance(x, bool):
        _die(f"Expected boolean for '{key}', got {type(x).__name__}")
    return x


def _as_str(x: Any, key: str) -> str:
    if not isinstance(x, str) or not x.strip():
        _die(f"Expected non-empty string for '{key}', got {repr(x)}")
    return x


def _as_num(x: Any, key: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        _die(f"Expected number for '{key}', got {type(x).__name__}")
    return float(x)


def _parse_iso(ts: str) -> None:
    # Our producer emits "+00:00" offset format; datetime.fromisoformat handles it.
    try:
        datetime.fromisoformat(ts)
    except Exception:
        _die(f"timestamp_utc is not ISO-8601 parseable: {ts!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Path to refusal_smoke_result.json")
    args = ap.parse_args()

    p = Path(args.inp)
    if not p.exists():
        _die(f"Input file not found: {p}")

    d = _read_json(p)

    # Required keys
    dry_run = _as_bool(d.get("dry_run"), "dry_run")
    ts = _as_str(d.get("timestamp_utc"), "timestamp_utc")
    _parse_iso(ts)

    _as_str(d.get("dataset"), "dataset")
    _as_str(d.get("model"), "model")
    _as_str(d.get("run_id"), "run_id")

    status = d.get("status")
    if status is not None and not isinstance(status, str):
        _die(f"Expected 'status' to be string|null, got {type(status).__name__}")
    status_s = (status or "").strip()

    rc = d.get("result_counts")
    if not isinstance(rc, dict):
        _die("result_counts must be an object")

    total = _as_int(rc.get("total"), "result_counts.total")
    passed = _as_int(rc.get("passed"), "result_counts.passed")
    failed = _as_int(rc.get("failed"), "result_counts.failed")
    errored = _as_int(rc.get("errored"), "result_counts.errored")

    # Loose sanity: don't overconstrain, but catch obvious nonsense
    if passed + failed + errored > total:
        _die(
            f"result_counts invalid: passed+failed+errored ({passed+failed+errored}) "
            f"> total ({total})"
        )

    fail_rate = _as_num(d.get("fail_rate"), "fail_rate")
    if total == 0:
        # Producer sets 1.0 in this case (fail-closed)
        if fail_rate < 0.0:
            _die(f"fail_rate must be >= 0.0, got {fail_rate}")
    else:
        expected = failed / total
        # tolerate tiny float noise
        if abs(fail_rate - expected) > 1e-9:
            _die(f"fail_rate mismatch: expected {expected}, got {fail_rate}")

    gate_key = _as_str(d.get("gate_key"), "gate_key")
    gate_pass = _as_bool(d.get("gate_pass"), "gate_pass")

    # Core semantics (fail-closed)
    expected_gate = (status_s in OK_STATUSES) and (total > 0) and (failed == 0) and (errored == 0)
    if gate_pass != expected_gate:
        _die(
            f"gate_pass does not match semantics for {gate_key}: "
            f"expected {expected_gate} from (status in {sorted(OK_STATUSES)}, total>0, failed==0, errored==0), "
            f"got {gate_pass} (status={status_s!r}, total={total}, failed={failed}, errored={errored})"
        )

    # Optional keys shape checks (non-fatal strictness)
    for opt in ("file_id", "eval_id", "report_url"):
        if opt in d and d[opt] is not None and not isinstance(d[opt], str):
            _die(f"{opt} must be string|null if present, got {type(d[opt]).__name__}")

    # Dry-run expectation: must not require network-only fields, but may include placeholders
    if dry_run and status_s == "":
        _die("In dry-run, status should be set (producer uses 'succeeded').")

    print(f"OK: contract valid for {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
