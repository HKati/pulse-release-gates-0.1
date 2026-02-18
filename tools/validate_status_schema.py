#!/usr/bin/env python3
"""
Fail-closed JSON Schema validation for PULSE status artifacts.

This tool is intentionally minimal and CI-friendly:
- validates a status JSON instance against a given JSON Schema
- emits GitHub Actions-style ::error:: annotations
- exits non-zero on any validation or IO failure

Exit codes:
  0 - OK (schema-valid)
  1 - validation / IO / parse error (fail-closed)
  2 - missing optional dependency (jsonschema)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _err(msg: str) -> None:
    print(f"::error::{msg}")


def _notice(msg: str) -> None:
    print(f"::notice::{msg}")


def _parse_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        _err(f"Failed to parse JSON: {path}: {e}")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--schema", required=True, help="Path to JSON Schema (Draft 2020-12)")
    ap.add_argument("--status", required=True, help="Path to status JSON to validate")
    ap.add_argument(
        "--max-errors",
        type=int,
        default=50,
        help="Maximum number of validation errors to emit (computation-capped)",
    )
    args = ap.parse_args()

    schema_path = Path(args.schema)
    status_path = Path(args.status)

    if not schema_path.is_file():
        _err(f"Schema not found at {schema_path}")
        return 1
    if not status_path.is_file():
        _err(f"status.json not found at {status_path}")
        return 1

    schema = _parse_json(schema_path)
    if not isinstance(schema, dict):
        _err(f"Schema file is not a JSON object: {schema_path}")
        return 1

    inst = _parse_json(status_path)
    if not isinstance(inst, dict):
        _err(f"Status file is not a JSON object: {status_path}")
        return 1

    # Lazy import so dependency-light environments produce a clean CI-friendly error.
    try:
        from jsonschema import Draft202012Validator  # type: ignore
    except ModuleNotFoundError:
        _err("Missing dependency: 'jsonschema'. Install it with: pip install jsonschema")
        return 2

    try:
        Draft202012Validator.check_schema(schema)
    except Exception as e:
        _err(f"Invalid JSON Schema ({schema_path}): {e}")
        return 1

    v = Draft202012Validator(schema)

    max_errors = int(args.max_errors) if args.max_errors is not None else 50
    if max_errors <= 0:
        max_errors = 1

    collected = []
    truncated = False

    for err in v.iter_errors(inst):
        collected.append(err)
        if len(collected) >= max_errors:
            truncated = True
            break

    # Deterministic ordering for the reported subset.
    collected.sort(key=lambda e: (tuple(str(p) for p in e.path), str(e.message)))

    if collected:
        _err("status.json schema validation failed:")
        for e in collected:
            path = ".".join(str(p) for p in e.path) or "<root>"
            _err(f"{path}: {e.message}")
        if truncated:
            _notice(f"Output truncated to --max-errors={max_errors}")
        return 1

    print(f"OK: schema-valid: {status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
