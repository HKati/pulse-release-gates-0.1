#!/usr/bin/env python3
"""
Fail-closed JSON Schema validation for PULSE status artifacts.

Design goals:
- Validate a status JSON against a given JSON Schema (Draft 2020-12).
- Emit GitHub Actions compatible ::error annotations for triage.
- Fail-closed on any validation error.
- Be CI-friendly: avoid unbounded error collection (respect --max-errors).
- Be local-friendly: if jsonschema is missing, emit a helpful error instead of a traceback.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _ga_error(msg: str, *, file: Path | None = None) -> None:
    if file is not None:
        print(f"::error file={file}::{msg}")
    else:
        print(f"::error::{msg}")


def _ga_notice(msg: str) -> None:
    print(f"::notice::{msg}")


def _load_json(path: Path, *, label: str) -> Any | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as e:
        _ga_error(f"Failed to read {label}: {e}", file=path)
        return None

    try:
        return json.loads(raw)
    except Exception as e:
        _ga_error(f"Failed to parse {label} as JSON: {e}", file=path)
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="validate_status_schema.py",
        description="Fail-closed validation of a status.json artifact against a JSON Schema.",
    )
    ap.add_argument("--schema", required=True, help="Path to JSON Schema (Draft 2020-12).")
    ap.add_argument("--status", required=True, help="Path to status.json to validate.")
    ap.add_argument(
        "--max-errors",
        type=int,
        default=50,
        help="Maximum number of validation errors to print (also bounds computation).",
    )
    args = ap.parse_args(argv)

    schema_path = Path(args.schema)
    status_path = Path(args.status)

    if args.max_errors <= 0:
        _ga_error("--max-errors must be a positive integer.")
        return 2

    if not schema_path.is_file():
        _ga_error("status schema not found", file=schema_path)
        return 1

    if not status_path.is_file():
        _ga_error("status.json not found", file=status_path)
        return 1

    schema = _load_json(schema_path, label="JSON Schema")
    if schema is None:
        return 1

    inst = _load_json(status_path, label="status JSON")
    if inst is None:
        return 1

    # Import jsonschema lazily so missing dependency yields a nice ::error instead of a traceback.
    try:
        from jsonschema import Draft202012Validator  # type: ignore
    except ModuleNotFoundError:
        _ga_error(
            "Missing dependency 'jsonschema'. Install it with: python -m pip install jsonschema"
        )
        return 2
    except Exception as e:
        _ga_error(f"Failed to import jsonschema: {e}")
        return 2

    try:
        Draft202012Validator.check_schema(schema)
    except Exception as e:
        _ga_error(f"Invalid JSON Schema: {e}", file=schema_path)
        return 1

    validator = Draft202012Validator(schema)

    # Bound computation: do not collect unlimited errors, respect --max-errors.
    errors = []
    truncated = False
    try:
        for err in validator.iter_errors(inst):
            errors.append(err)
            if len(errors) > args.max_errors:
                truncated = True
                errors = errors[: args.max_errors]
                break
    except Exception as e:
        _ga_error(f"Validator crashed while iterating errors: {e}", file=status_path)
        return 1

    if errors:
        # Sort only the bounded list for stable output.
        errors_sorted = sorted(errors, key=lambda e: (list(e.path), e.message))

        _ga_error(
            f"status.json schema validation failed (showing {len(errors_sorted)} error(s)).",
            file=status_path,
        )
        for e in errors_sorted:
            path = ".".join(str(p) for p in e.path) or "<root>"
            _ga_error(f"{path}: {e.message}", file=status_path)

        if truncated:
            _ga_notice(f"Validation output truncated to first {args.max_errors} errors.")
        return 1

    print(f"OK: schema-valid: {status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
