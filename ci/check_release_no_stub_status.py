#!/usr/bin/env python3
"""Release-grade fail-closed guard against stubbed status artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def die(message: str) -> None:
    print(f"[release-no-stub:error] {message}", file=sys.stderr)
    raise SystemExit(1)


def expect_dict(name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        die(f"expected {name} object, got {type(value).__name__}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed release-grade guard for non-stubbed status evidence."
    )
    parser.add_argument("--status", required=True, help="Path to status.json")
    args = parser.parse_args()

    try:
        status = json.loads(Path(args.status).read_text(encoding="utf-8"))
    except Exception as exc:
        die(f"failed to load status JSON: {exc}")

    status = expect_dict("status", status)
    gates = expect_dict("status.gates", status.get("gates"))
    diagnostics = expect_dict("status.diagnostics", status.get("diagnostics"))

    det_ok = gates.get("detectors_materialized_ok")
    if det_ok is not True:
        die(
            "release-grade run requires "
            "gates.detectors_materialized_ok to be literal true"
        )

    gates_stubbed = diagnostics.get("gates_stubbed")
    if gates_stubbed is not False:
        die(
            "release-grade run requires "
            "diagnostics.gates_stubbed to be literal false"
        )

    scaffold = diagnostics.get("scaffold")
    if scaffold is not False:
        die(
            "release-grade run requires "
            "diagnostics.scaffold to be literal false"
        )

    print("OK: release-grade status is materialized and explicitly non-stubbed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
