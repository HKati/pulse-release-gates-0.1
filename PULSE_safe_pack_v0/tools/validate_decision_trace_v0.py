#!/usr/bin/env python3
"""
validate_decision_trace_v0.py

Small helper to validate a decision trace JSON file against the
PULSE_decision_trace_v0.schema.json schema.

Special case:
- we tolerate missing `details.instability_components` for backward
  compatibility, but report a warning.
- all other schema violations remain hard errors.
"""

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_trace(trace_path: Path, schema_path: Path) -> int:
    trace = load_json(trace_path)
    schema = load_json(schema_path)

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(trace), key=lambda e: e.path)

    hard_errors = []
    warned_missing_instability_components = False

    for err in errors:
        # Tolerate exactly this one case:
        #   - "instability_components" is a required property
        #   - at JSON path: details
        if (
            err.validator == "required"
            and isinstance(err.validator_value, list)
            and "instability_components" in err.validator_value
            and list(err.path) == ["details"]
        ):
            if not warned_missing_instability_components:
                print(
                    "[validate_decision_trace_v0] WARNING: "
                    "missing 'details.instability_components'. "
                    "Tolerating for backward compatibility."
                )
                warned_missing_instability_components = True
            # do not treat this as a hard error
            continue

        hard_errors.append(err)

    if hard_errors:
        print("[validate_decision_trace_v0] Validation FAILED.")
        print(f"- Trace:  {trace_path}")
        print(f"- Schema: {schema_path}")
        print("\nDetails:")
        for err in hard_errors:
            json_path = "/".join(str(p) for p in err.path) or "<root>"
            print(f"  - {err.message}")
            print(f"    at JSON path: {json_path}")
        return 1

    print("[validate_decision_trace_v0] Validation OK.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate decision_trace JSON against v0 schema."
    )
    parser.add_argument(
        "trace_json",
        type=Path,
        help="Path to decision_trace JSON file.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        required=True,
        help="Path to PULSE_decision_trace_v0.schema.json.",
    )

    args = parser.parse_args()
    exit_code = validate_trace(args.trace_json, args.schema)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
