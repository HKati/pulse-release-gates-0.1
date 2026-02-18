#!/usr/bin/env python3
"""
Export PULSE gate results from status.json to a SARIF 2.1.0 report.

Design goals:
- Deterministic output (sorted gates, stable formatting).
- Backwards compatible CLI/env interface:
  * --status optional; falls back to $PULSE_STATUS, then pack artifacts/status.json
  * --out optional; falls back to $PULSE_SARIF, then ./reports/sarif.json

NOTE:
- Reporting helper only. Fail-closed enforcement is handled by check_gates.py.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
from datetime import datetime, timezone
from typing import Any


def gh_warn(msg: str) -> None:
    print(f"::warning::{msg}")


def gh_error(msg: str) -> None:
    print(f"::error::{msg}")


def safe_read_json(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        gh_error(f"Failed to read/parse JSON at {path}: {e}")
        return None


def _boolish(v: Any) -> bool:
    # Only literal True counts as pass (fail-closed convention)
    return v is True


def _default_status_path() -> pathlib.Path:
    env = os.getenv("PULSE_STATUS")
    if isinstance(env, str) and env.strip():
        return pathlib.Path(env.strip())
    pack_root = pathlib.Path(__file__).resolve().parents[1]  # PULSE_safe_pack_v0
    return pack_root / "artifacts" / "status.json"


def _default_out_path() -> pathlib.Path:
    env = os.getenv("PULSE_SARIF")
    if isinstance(env, str) and env.strip():
        return pathlib.Path(env.strip())
    return pathlib.Path("reports") / "sarif.json"


def _now_utc_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--status", default="", help="Path to status.json (default: $PULSE_STATUS or pack artifacts/status.json)")
    ap.add_argument("--out", default="", help="Output path for SARIF JSON (default: $PULSE_SARIF or ./reports/sarif.json)")
    ap.add_argument("--tool-name", default="PULSE", help="SARIF tool.driver.name")
    args = ap.parse_args()

    status_path = pathlib.Path(args.status) if str(args.status).strip() else _default_status_path()
    out_path = pathlib.Path(args.out) if str(args.out).strip() else _default_out_path()

    if not status_path.exists():
        gh_warn(f"status.json not found at {status_path}; skipping SARIF export.")
        return 0

    status = safe_read_json(status_path)
    if not isinstance(status, dict):
        gh_warn("status.json is not a JSON object; skipping SARIF export.")
        return 0

    gates = status.get("gates") or {}
    if not isinstance(gates, dict):
        gates = {}

    gate_ids = sorted((str(k) for k in gates.keys()), key=lambda x: x)

    # Deterministic rule set (all gates become rules; only failing gates become results)
    rules: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    # Prefer status.created_utc for a stable-ish run timestamp; fallback to wall clock.
    created_utc = status.get("created_utc")
    start_time = str(created_utc) if isinstance(created_utc, str) and created_utc.strip() else _now_utc_z()

    for gid in gate_ids:
        rules.append(
            {
                "id": gid,
                "shortDescription": {"text": gid},
                "defaultConfiguration": {"level": "error"},
            }
        )

        ok = _boolish(gates.get(gid))
        if ok:
            continue

        results.append(
            {
                "ruleId": gid,
                "level": "error",
                "message": {"text": f"PULSE gate failed: {gid}"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": str(status_path)},
                            "region": {"startLine": 1},
                        }
                    }
                ],
                "properties": {
                    "gate_value": gates.get(gid),
                    "status_version": status.get("version", ""),
                    "created_utc": created_utc or "",
                },
            }
        )

    sarif = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {"driver": {"name": str(args.tool_name), "rules": rules}},
                "results": results,
                "invocations": [{"executionSuccessful": True, "startTimeUtc": start_time}],
            }
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        out_path.write_text(json.dumps(sarif, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as e:
        gh_error(f"Failed to write SARIF JSON to {out_path}: {e}")
        return 1

    print(f"OK: wrote SARIF report: {out_path} (rules={len(rules)}, results={len(results)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
