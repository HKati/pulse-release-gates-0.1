#!/usr/bin/env python3
"""Check that the Parameter Golf v0 example receipt is reproducible.

This is a shadow-only deterministic roundtrip check:
example evidence -> receipt renderer -> committed example receipt.

In addition to deterministic equality, this script validates both the
committed example receipt and the freshly rendered receipt against the
review-receipt schema.
"""

from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from verify_parameter_golf_submission_v0 import MissingDependencyError, _load_jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = REPO_ROOT / "examples/parameter_golf_submission_evidence_v0.example.json"
DEFAULT_SCHEMA = REPO_ROOT / "schemas/parameter_golf_submission_evidence_v0.schema.json"
DEFAULT_RECEIPT_SCHEMA = (
    REPO_ROOT / "schemas/parameter_golf_submission_review_receipt_v0.schema.json"
)
DEFAULT_RENDERER = REPO_ROOT / "tools/render_parameter_golf_review_receipt_v0.py"
DEFAULT_EXPECTED = REPO_ROOT / "examples/parameter_golf_submission_review_receipt_v0.example.json"


class RoundtripError(Exception):
    """Raised when the roundtrip check cannot be executed."""


class RoundtripFailure(Exception):
    """Raised when the rendered or expected receipt fails the roundtrip contract."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check that the Parameter Golf v0 example evidence renders to the "
            "committed example review receipt and that both receipts validate "
            "against the review-receipt schema."
        )
    )
    parser.add_argument(
        "--evidence",
        default=str(DEFAULT_EVIDENCE),
        help="Path to the example evidence artifact.",
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA),
        help="Path to the evidence schema JSON.",
    )
    parser.add_argument(
        "--receipt-schema",
        default=str(DEFAULT_RECEIPT_SCHEMA),
        help="Path to the review-receipt schema JSON.",
    )
    parser.add_argument(
        "--renderer",
        default=str(DEFAULT_RENDERER),
        help="Path to the review receipt renderer.",
    )
    parser.add_argument(
        "--expected",
        default=str(DEFAULT_EXPECTED),
        help="Path to the committed expected review receipt.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RoundtripError(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RoundtripError(f"Invalid JSON in {path}: {exc}") from exc


def render_receipt(
    *,
    renderer_path: Path,
    evidence_path: Path,
    schema_path: Path,
) -> dict[str, Any]:
    if not renderer_path.exists():
        raise RoundtripError(f"Renderer script not found: {renderer_path}")
    if not evidence_path.exists():
        raise RoundtripError(f"Evidence artifact not found: {evidence_path}")
    if not schema_path.exists():
        raise RoundtripError(f"Schema file not found: {schema_path}")

    with tempfile.TemporaryDirectory(prefix="pg_receipt_roundtrip_") as tmpdir:
        output_path = Path(tmpdir) / "rendered_receipt.json"
        cmd = [
            sys.executable,
            str(renderer_path),
            "--evidence",
            str(evidence_path),
            "--schema",
            str(schema_path),
            "--output",
            str(output_path),
        ]
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RoundtripError(
                "Renderer exited non-zero during roundtrip check.\n"
                f"Command: {' '.join(cmd)}\n"
                f"Return code: {proc.returncode}\n"
                f"STDOUT:\n{proc.stdout}\n"
                f"STDERR:\n{proc.stderr}"
            )
        if not output_path.exists():
            raise RoundtripError(
                "Renderer completed without writing the output receipt file.\n"
                f"Expected path: {output_path}"
            )
        rendered = load_json(output_path)
        if not isinstance(rendered, dict):
            raise RoundtripError(
                f"Renderer output must be a JSON object, got: {type(rendered).__name__}"
            )
        return rendered


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def unified_diff(expected: Any, actual: Any) -> str:
    expected_text = canonical_json(expected).splitlines(keepends=True)
    actual_text = canonical_json(actual).splitlines(keepends=True)
    diff = difflib.unified_diff(
        expected_text,
        actual_text,
        fromfile="expected",
        tofile="rendered",
    )
    return "".join(diff)


def _render_path(path_value: list[Any]) -> str:
    if not path_value:
        return "<root>"
    return "/".join(str(p) for p in path_value)


def load_and_check_receipt_schema(path: Path) -> tuple[Any, dict[str, Any] | bool]:
    if not path.exists():
        raise RoundtripError(f"Receipt schema file not found: {path}")

    schema = load_json(path)

    try:
        jsonschema_mod = _load_jsonschema()
    except MissingDependencyError as exc:
        raise RoundtripError(str(exc)) from exc

    if not isinstance(schema, (dict, bool)):
        raise RoundtripError(
            f"Receipt schema must be a JSON object or boolean schema: {path}"
        )

    try:
        validator_cls = jsonschema_mod.validators.validator_for(schema)
        validator_cls.check_schema(schema)
    except TypeError as exc:
        raise RoundtripError(f"Invalid receipt schema in {path}: {exc}") from exc
    except jsonschema_mod.SchemaError as exc:
        raise RoundtripError(f"Invalid receipt schema in {path}: {exc.message}") from exc

    return jsonschema_mod, schema


def assert_valid_receipt(
    payload: Any,
    *,
    schema: dict[str, Any] | bool,
    jsonschema_mod: Any,
    label: str,
) -> None:
    try:
        validator_cls = jsonschema_mod.validators.validator_for(schema)
        validator_cls.check_schema(schema)
        validator = validator_cls(schema)
        validator.validate(payload)
    except jsonschema_mod.ValidationError as exc:
        location = _render_path(list(exc.absolute_path))
        raise RoundtripFailure(
            f"{label} failed receipt schema validation at {location}: {exc.message}"
        ) from exc
    except jsonschema_mod.SchemaError as exc:
        raise RoundtripError(f"Receipt schema is invalid: {exc.message}") from exc


def main() -> int:
    args = parse_args()
    evidence_path = Path(args.evidence)
    schema_path = Path(args.schema)
    receipt_schema_path = Path(args.receipt_schema)
    renderer_path = Path(args.renderer)
    expected_path = Path(args.expected)

    try:
        expected = load_json(expected_path)
        actual = render_receipt(
            renderer_path=renderer_path,
            evidence_path=evidence_path,
            schema_path=schema_path,
        )
        jsonschema_mod, receipt_schema = load_and_check_receipt_schema(receipt_schema_path)
        assert_valid_receipt(
            expected,
            schema=receipt_schema,
            jsonschema_mod=jsonschema_mod,
            label=f"committed expected receipt ({expected_path})",
        )
        assert_valid_receipt(
            actual,
            schema=receipt_schema,
            jsonschema_mod=jsonschema_mod,
            label="rendered receipt",
        )
    except RoundtripFailure as exc:
        print(f"ROUNDTRIP FAIL: {exc}", file=sys.stderr)
        return 1
    except RoundtripError as exc:
        print(f"ROUNDTRIP ERROR: {exc}", file=sys.stderr)
        return 2

    if actual != expected:
        print(
            "ROUNDTRIP FAIL: rendered receipt does not match the committed example.",
            file=sys.stderr,
        )
        diff = unified_diff(expected, actual)
        if diff:
            print(diff, file=sys.stderr, end="")
        return 1

    print("ROUNDTRIP PASS: example evidence renders to the committed example receipt.")
    print(f"evidence        : {evidence_path}")
    print(f"schema          : {schema_path}")
    print(f"receipt schema  : {receipt_schema_path}")
    print(f"renderer        : {renderer_path}")
    print(f"expected        : {expected_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
