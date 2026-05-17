#!/usr/bin/env python3
"""Release-grade fail-closed guard against stubbed status artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def die(msg: str) -> None:
    print(f"[release-no-stub:error] {msg}", file=sys.stderr)
    raise SystemExit(1)


def expect_dict(name: str, obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        die(f"expected {name} object, got {type(obj).__name__}")
    return obj


def expect_bool(name: str, obj: Any) -> bool:
    if not isinstance(obj, bool):
        die(f"expected {name} bool, got {type(obj).__name__}")
    return obj


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--status", required=True)
    args = p.parse_args()

    try:
        status = json.loads(Path(args.status).read_text(encoding="utf-8"))
    except Exception as exc:
        die(f"failed to load status JSON: {exc}")

    status = expect_dict("status", status)
    gates = expect_dict("status.gates", status.get("gates"))
    diagnostics = expect_dict("status.diagnostics", status.get("diagnostics"))

    det_ok = expect_bool("gates.detectors_materialized_ok", gates.get("detectors_materialized_ok"))
    if det_ok is not True:
        die("release-grade run requires gates.detectors_materialized_ok=true")

    gates_stubbed = expect_bool("diagnostics.gates_stubbed", diagnostics.get("gates_stubbed"))
    if gates_stubbed:
        die("release-grade run must not emit diagnostics.gates_stubbed=true")

    scaffold = expect_bool("diagnostics.scaffold", diagnostics.get("scaffold"))
    if scaffold:
        die("release-grade run must not emit diagnostics.scaffold=true")

    print("OK: release-grade status is materialized and non-stubbed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
