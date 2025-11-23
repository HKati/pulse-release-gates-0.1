#!/usr/bin/env python
"""
validate_decision_trace_v0.py

Small CLI helper to validate a decision trace JSON artefact against
the PULSE_decision_trace_v0 schema.

This is a developer tool:
- it does NOT run in the gate,
- it does NOT change any decisions,
- it only validates structure and types of the exported trace.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load_json(path: Path) -> Optional[Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[validate_decision_trace_v0] ERROR: file not found: {path}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(
            f"[validate_decision_trace_v0] ERROR: invalid JSON in {path}: {e}",
            file=sys.stderr,
        )
        return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a decision trace JSON against the PULSE_decision_trace_v0 schema."
    )
    parser.add_argument(
        "--trace",
        "--input",
        dest="trace_path",
        default="PULSE_safe_pack_v0/artifacts/decision_trace.demo.ci.json",
        help=(
            "Path to the decision trace JSON to validate "
            "(default: PULSE_safe_pack_v0/artifacts/decision_trace.demo.ci.json)"
        ),
    )
    parser.add_argument(
        "--schema",
        "--schema-path",
        dest="schema_path",
        default="schemas/PULSE_decision_trace_v0.schema.json",
        help=(
            "Path to the JSON-schema file for decision trace v0 "
            "(default: schemas/PULSE_decision_trace_v0.schema.json)"
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero when any validation error is found (default).",
    )
    parser.add_argument(
        "--non-strict",
        dest="strict",
        action="store_false",
        help="Exit with zero even if validation errors are found (log only).",
    )
    parser.set_defaults(strict=True)
    return parser.parse_args()


def _validate(trace: Any, schema: Any) -> List[str]:
    """
    Run jsonschema validation and return a list of human-readable error strings.
    """
    try:
        import jsonschema
    except ImportError:
        print(
            "[validate_decision_trace_v0] ERROR: jsonschema is not installed.\n"
            "Install it with: pip install jsonschema",
            file=sys.stderr,
        )
        return ["missing jsonschema dependency"]

    validator = jsonschema.Draft7Validator(schema)
    errors: List[str] = []

    for err in sorted(validator.iter_errors(trace), key=lambda e: e.path):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{loc}: {err.message}")

    return errors


def main() -> None:
    args = _parse_args()

    trace_path = Path(args.trace_path)
    schema_path = Path(args.schema_path)

    trace = _load_json(trace_path)
    if trace is None:
        sys.exit(1)

    schema = _load_json(schema_path)
    if schema is None:
        sys.exit(1)

    errors = _validate(trace, schema)
    if not errors:
        print(
            f"[validate_decision_trace_v0] OK: {trace_path} "
            f"conforms to {schema_path.name}"
        )
        sys.exit(0)

    print(
        f"[validate_decision_trace_v0] Found {len(errors)} validation error(s) "
        f"for {trace_path}:",
        file=sys.stderr,
    )
    for msg in errors:
        print(f"  - {msg}", file=sys.stderr)

    if args.strict:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
