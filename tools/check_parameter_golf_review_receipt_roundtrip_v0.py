#!/usr/bin/env python3
"""Check that the Parameter Golf v0 example receipt is reproducible.

This is a shadow-only deterministic roundtrip check:

example evidence -> receipt renderer -> committed example receipt
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


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = REPO_ROOT / "examples/parameter_golf_submission_evidence_v0.example.json"
DEFAULT_SCHEMA = REPO_ROOT / "schemas/parameter_golf_submission_evidence_v0.schema.json"
DEFAULT_RENDERER = REPO_ROOT / "tools/render_parameter_golf_review_receipt_v0.py"
DEFAULT_EXPECTED = REPO_ROOT / "examples/parameter_golf_submission_review_receipt_v0.example.json"


class RoundtripError(Exception):
    """Raised when the roundtrip check cannot be executed."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check that the Parameter Golf v0 example evidence renders to the "
            "committed example review receipt."
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


def load_json(path: Path) -> dict[str, Any]:
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

        return load_json(output_path)


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def unified_diff(expected: dict[str, Any], actual: dict[str, Any]) -> str:
    expected_text = canonical_json(expected).splitlines(keepends=True)
    actual_text = canonical_json(actual).splitlines(keepends=True)
    diff = difflib.unified_diff(
        expected_text,
        actual_text,
        fromfile="expected",
        tofile="rendered",
    )
    return "".join(diff)


def main() -> int:
    args = parse_args()

    evidence_path = Path(args.evidence)
    schema_path = Path(args.schema)
    renderer_path = Path(args.renderer)
    expected_path = Path(args.expected)

    try:
        expected = load_json(expected_path)
        actual = render_receipt(
            renderer_path=renderer_path,
            evidence_path=evidence_path,
            schema_path=schema_path,
        )
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
    print(f"evidence : {evidence_path}")
    print(f"schema   : {schema_path}")
    print(f"renderer : {renderer_path}")
    print(f"expected : {expected_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
