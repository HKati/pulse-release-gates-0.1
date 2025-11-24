import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

import jsonschema


def _normalise_trace_for_validation(trace: Dict[str, Any]) -> Dict[str, Any]:
    """Apply small backwards-compatibility shims before validation."""

    details = trace.get("details")
    if isinstance(details, dict):
        # Older/demo traces may not populate this yet; the schema requires it.
        details.setdefault("instability_components", [])

    return trace


def validate_decision_trace(
    trace_path: Path,
    schema_path: Path,
    *,
    label: str = "validate_decision_trace_v0",
) -> bool:
    """Validate a decision_trace_v0 artefact against its JSONSchema.

    Returns:
        True if validation passes, False if there are schema errors.
    """
    with trace_path.open("r", encoding="utf-8") as f:
        trace = json.load(f)

    # Backwards-compat shim for older traces
    trace = _normalise_trace_for_validation(trace)

    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)

    validator = jsonschema.Draft2020Validator(schema)
    errors = sorted(validator.iter_errors(trace), key=lambda e: list(e.path))

    if errors:
        print(f"[{label}] validation FAILED.")
        print(f"- Trace:  {trace_path}")
        print(f"- Schema: {schema_path}")
        print()
        print("Details:")
        for err in errors:
            path = "/".join(str(p) for p in err.path) or "<root>"
            print(f"  - {err.message}")
            print(f"    at JSON path: {path}")
        return False

    print(f"[{label}] validation OK.")
    print(f"- Trace:  {trace_path}")
    print(f"- Schema: {schema_path}")
    return True


def validate_decision_trace_v0(
    trace_path: Path,
    schema_path: Path,
    *,
    label: str = "validate_decision_trace_v0",
) -> bool:
    """Compatibility wrapper with the historical function name."""
    return validate_decision_trace(trace_path, schema_path, label=label)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a PULSE decision_trace_v0 artefact against its JSONSchema."
    )
    parser.add_argument(
        "--trace",
        required=True,
        help="Path to decision_trace_v0 JSON artefact.",
    )
    parser.add_argument(
        "--schema",
        required=True,
        help="Path to PULSE_decision_trace_v0.schema.json.",
    )
    parser.add_argument(
        "--name",
        default="validate_decision_trace_v0",
        help="Label used in log output (defaults to 'validate_decision_trace_v0').",
    )
    return parser


def main(argv: Any = None) -> None:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    trace_path = Path(args.trace)
    schema_path = Path(args.schema)
    label = str(args.name)

    ok = validate_decision_trace(trace_path, schema_path, label=label)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
