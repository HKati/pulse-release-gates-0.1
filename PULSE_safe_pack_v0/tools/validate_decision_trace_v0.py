#!/usr/bin/env python
"""
validate_decision_trace_v0.py

Developer-only helper for validating decision trace JSON artefacts
against the PULSE_decision_trace_v0 JSON schema using jsonschema.

This tool is a shadow-only utility:
- it does NOT participate in any gate or deployment path,
- it is meant for local validation and optional CI usage.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

import jsonschema
from jsonschema.exceptions import ValidationError


def _load_json(path: Path, label: str) -> Any:
    """Load a JSON file with basic error handling."""
    if not path.exists():
        print(f"[validate_decision_trace_v0] {label} not found at: {path}")
        sys.exit(1)

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        print(
            f"[validate_decision_trace_v0] Failed to parse {label} as JSON: "
            f"{exc}"
        )
        sys.exit(1)


def _default_schema_path() -> Path:
    """Resolve the default schema path relative to this file.

    Layout assumption (repo root):
      - schemas/PULSE_decision_trace_v0.schema.json
      - PULSE_safe_pack_v0/tools/validate_decision_trace_v0.py  (this file)
    """
    here = Path(__file__).resolve()
    repo_root = here.parents[2]  # .../pulse-release-gates-0.1/
    return repo_root / "schemas" / "PULSE_decision_trace_v0.schema.json"


def validate_trace(trace_path: Path, schema_path: Path) -> bool:
    """Validate a decision_trace_v0 JSON against the given schema.

    Returns:
        True if validation succeeds, False otherwise.
    """
    trace = _load_json(trace_path, "decision trace")
    schema = _load_json(schema_path, "schema")

    try:
        jsonschema.validate(instance=trace, schema=schema)
    except ValidationError as exc:
        print("[validate_decision_trace_v0] Validation FAILED.")
        print(f"- Trace:  {trace_path}")
        print(f"- Schema: {schema_path}")
        print("")
        print("Details:")
        # Keep the message reasonably compact, but informative.
        print(f"  {exc.message}")
        if exc.path:
            path_str = " -> ".join(str(p) for p in exc.path)
            print(f"  at JSON path: {path_str}")
        sys.exit(1)

    print("[validate_decision_trace_v0] Validation OK.")
    print(f"- Trace:  {trace_path}")
    print(f"- Schema: {schema_path}")
    return True


def _parse_args(argv: Any = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate decision_trace_v0 JSON against its schema."
    )

    parser.add_argument(
        "trace",
        metavar="TRACE_JSON",
        type=str,
        help="Path to decision_trace_v0 JSON (e.g. decision_trace_v0.json)",
    )
    parser.add_argument(
        "--schema",
        type=str,
        default=None,
        help=(
            "Path to schema JSON "
            "(default: schemas/PULSE_decision_trace_v0.schema.json "
            "relative to repo root)"
        ),
    )

    return parser.parse_args(argv)


def main(argv: Any = None) -> int:
    args = _parse_args(argv)

    trace_path = Path(args.trace).expanduser().resolve()

    if args.schema is not None:
        schema_path = Path(args.schema).expanduser().resolve()
    else:
        schema_path = _default_schema_path()

    validate_trace(trace_path, schema_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
