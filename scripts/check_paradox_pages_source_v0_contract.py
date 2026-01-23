#!/usr/bin/env python3
"""
check_paradox_pages_source_v0_contract.py

Fail-closed contract checker for the Paradox Core Pages provenance manifest:

  _site/paradox/core/v0/source_v0.json

Design goals:
  - stdlib-only (no dependency drift)
  - deterministic (no timestamps, no external calls)
  - strict (no extra keys; fail-closed on any ambiguity)

Contract (v0):
  - schema == "PULSE_paradox_pages_source_v0"
  - version == "v0"
  - upstream_run_id: non-empty string
  - source: one of {"artifact_drift", "case_study"}
  - transitions_dir: non-empty string
  - no additional top-level keys
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


SCHEMA_NAME = "PULSE_paradox_pages_source_v0"
SCHEMA_VERSION = "v0"

ALLOWED_SOURCES = {"artifact_drift", "case_study"}

REQUIRED_KEYS: Tuple[str, ...] = (
    "schema",
    "version",
    "upstream_run_id",
    "source",
    "transitions_dir",
)

ALLOWED_KEYS = set(REQUIRED_KEYS)


def _fail(msg: str) -> int:
    print(f"CONTRACT FAIL: {msg}", file=sys.stderr)
    return 1


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to parse JSON: {e}") from e


def _is_nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _validate_root(obj: Any) -> Tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, "root must be a JSON object"
    return True, ""


def _validate_keys(obj: Dict[str, Any]) -> Tuple[bool, str]:
    missing = [k for k in REQUIRED_KEYS if k not in obj]
    if missing:
        return False, f"missing required keys: {missing}"

    extra = sorted(set(obj.keys()) - ALLOWED_KEYS)
    if extra:
        return False, f"unexpected extra keys (strict contract): {extra}"

    return True, ""


def _validate_values(obj: Dict[str, Any]) -> Tuple[bool, str]:
    if obj.get("schema") != SCHEMA_NAME:
        return False, f"schema must be '{SCHEMA_NAME}'"

    if obj.get("version") != SCHEMA_VERSION:
        return False, f"version must be '{SCHEMA_VERSION}'"

    upstream_run_id = obj.get("upstream_run_id")
    if not _is_nonempty_str(upstream_run_id):
        return False, "upstream_run_id must be a non-empty string"

    source = obj.get("source")
    if not _is_nonempty_str(source):
        return False, "source must be a non-empty string"
    if source not in ALLOWED_SOURCES:
        return False, f"source must be one of {sorted(ALLOWED_SOURCES)} (got: {source!r})"

    transitions_dir = obj.get("transitions_dir")
    if not _is_nonempty_str(transitions_dir):
        return False, "transitions_dir must be a non-empty string"

    # Hardening: avoid pathological values (still deterministic).
    for key in ("upstream_run_id", "source", "transitions_dir"):
        v = obj.get(key)
        if isinstance(v, str) and ("\x00" in v):
            return False, f"{key} contains NUL byte (\\x00), which is not allowed"

    return True, ""


def validate_source_v0(obj: Any) -> Tuple[bool, str]:
    ok, msg = _validate_root(obj)
    if not ok:
        return ok, msg

    assert isinstance(obj, dict)
    ok, msg = _validate_keys(obj)
    if not ok:
        return ok, msg

    ok, msg = _validate_values(obj)
    if not ok:
        return ok, msg

    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Path to source_v0.json")
    args = ap.parse_args()

    in_path = Path(args.in_path)

    if not in_path.exists():
        return _fail(f"input file not found: {in_path}")

    try:
        obj = _load_json(in_path)
    except FileNotFoundError:
        return _fail(f"input file not found: {in_path}")
    except Exception as e:
        return _fail(str(e))

    ok, msg = validate_source_v0(obj)
    if not ok:
        return _fail(msg)

    print(f"OK: source_v0 contract holds ({in_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
