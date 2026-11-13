#!/usr/bin/env python3
"""Emit a source-bound cyclic research report; never execute candidates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paradox_cyclic_v0.contract import CyclicError, encode_json, read_bytes
from paradox_cyclic_v0.evaluator import evaluate_bytes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, metavar="FILE")
    args = parser.parse_args(argv)
    try:
        report = evaluate_bytes(read_bytes(args.input))
    except CyclicError as error:
        sys.stderr.buffer.write(encode_json({
            "error": error.kind,
            "code": error.code,
            "authority_effect": "none",
            "production_gate_eligible": False,
        }))
        return 1
    sys.stdout.buffer.write(encode_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
