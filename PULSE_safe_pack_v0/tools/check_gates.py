#!/usr/bin/env python3
"""
PULSE check_gates.py

Deterministic, fail-closed enforcement of required gates from status.json.

PASS semantics (strict):
- A gate PASSES only if its value is the literal boolean True.
- Any other value (False, None, missing, string, number, etc.) is NOT PASS.

Exit codes:
- 0: all required gates PASS
- 1: at least one required gate is present but not literal True
- 2: status missing/invalid OR one or more required gates are missing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _load_status(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception as e:
        _eprint(f"[X] Failed to read/parse status JSON at {path}: {e}")
        return None


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", required=True, help="Path to status.json")
    ap.add_argument("--require", nargs="+", required=True, help="Gate IDs that must PASS")
    args = ap.parse_args(argv)

    status_path = Path(args.status)
    data = _load_status(status_path)
    if data is None or not isinstance(data, dict):
        _eprint(f"[X] Invalid or missing status.json: {status_path}")
        return 2

    gates = data.get("gates")
    if not isinstance(gates, dict):
        _eprint(f"[X] status.json is missing a 'gates' object: {status_path}")
        return 2

    required = _unique_preserve_order([str(x) for x in args.require])

    missing = [k for k in required if k not in gates]
    if missing:
        print("[X] Missing required gates:", ", ".join(missing))
        return 2

    # Strict: True-only PASS
    failing = [k for k in required if gates.get(k) is not True]
    if failing:
        print("[X] FAIL gates:", ", ".join(failing))
        # Helpful values for CI logs
        details = ", ".join(f"{k}={json.dumps(gates.get(k), ensure_ascii=False)}" for k in failing)
        print("[X] Values:", details)
        return 1

    print("[OK] All required gates PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
