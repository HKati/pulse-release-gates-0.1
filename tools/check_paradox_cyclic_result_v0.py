#!/usr/bin/env python3
"""Check a cyclic research report against its exact input bytes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paradox_cyclic_v0.checker import verify_bytes
from paradox_cyclic_v0.contract import CyclicError, encode_json, read_bytes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, metavar="FILE")
    parser.add_argument("--report", required=True, metavar="FILE")
    args = parser.parse_args(argv)
    try:
        input_raw = read_bytes(args.input)
        try:
            report_raw = read_bytes(args.report)
        except CyclicError as error:
            raise CyclicError("REPORT_FILE_REJECTED", "REPORT_REJECTED") from error
        verification = verify_bytes(input_raw, report_raw)
    except CyclicError as error:
        sys.stderr.buffer.write(encode_json({
            "error": error.kind,
            "code": error.code,
            "authority_effect": "none",
            "production_gate_eligible": False,
        }))
        return 1
    sys.stdout.buffer.write(encode_json(verification))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
