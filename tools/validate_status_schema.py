#!/usr/bin/env python3
"""
Fail-closed JSON Schema validation for PULSE status artifacts.

This tool is intentionally minimal and CI-friendly:
- validates a status JSON instance against a given JSON Schema
- emits GitHub Actions ::error annotations
- fails closed on any validation error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--schema", required=True, help="Path to JSON Schema file")
    ap.add_argument("--status", required=True, help="Path to status JSON instance")
    ap.add_argument("--max-errors", type=int, default=50, help="Max number of errors to print")
    args = ap.parse_args()

    # Dependency check (fail-closed with a clear message)
    try:
        from jsonschema import Draft202012Validator  # type: ignore
    except ModuleNotFoundError:
        print("::error::Missing Python dependency: 'jsonschema'")
        print("::error::Install it with: python -m pip install jsonschema")
        return 2
    except Exception as e:
        print(f"::error::Failed to import jsonschema: {e}")
        return 2

    schema_path = Path(args.schema)
    status_path = Path(args.status)

    if not schema_path.is_file():
        print(f"::error file={schema_path}::Schema not found")
        return 1

    if not status_path.is_file():
        print(f"::error file={status_path}::Status JSON not found")
        return 1

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"::error file={schema_path}::Failed to parse schema JSON: {e}")
        return 1

    try:
        Draft202012Validator.check_schema(schema)
        v = Draft202012Validator(schema)
    except Exception as e:
        print(f"::error file={schema_path}::Invalid JSON Schema: {e}")
        return 1

    try:
        inst = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"::error file={status_path}::Failed to parse status JSON: {e}")
        return 1

    errors = sorted(v.iter_errors(inst), key=lambda e: (list(e.path), e.message))
    if errors:
        print(f"::error::status schema validation failed for {status_path}")
        limit = max(1, int(args.max_errors))
        for e in errors[:limit]:
            path = ".".join(str(p) for p in e.path) or "<root>"
            print(f"::error file={status_path}::{path}: {e.message}")
        if len(errors) > limit:
            print(f"::error::... {len(errors) - limit} more error(s) truncated")
        return 1

    print(f"OK: schema-valid: {status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
