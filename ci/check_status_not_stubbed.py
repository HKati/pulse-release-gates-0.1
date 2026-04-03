#!/usr/bin/env python3
"""Fail-closed status.json guard for canonical lanes.

This helper checks that a status.json artifact is not scaffold/stub output.
It is intended for canonical core / release lanes where shadow or placeholder
gate booleans must never be treated as real release evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


def _die(msg: str) -> None:
    print(f"[status-guard:error] {msg}", file=sys.stderr)
    raise SystemExit(1)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _die(f"status.json not found: {path}")
    except json.JSONDecodeError as exc:
        _die(f"invalid JSON in {path}: {exc}")

    if not isinstance(data, dict):
        _die(f"top-level JSON must be an object, got {type(data).__name__}")
    return data


def _expect_object(name: str, value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        _die(f"expected '{name}' to be an object, got {type(value).__name__}")
    return value


def _expect_bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        _die(f"expected '{name}' to be a boolean, got {type(value).__name__}")
    return value


def _expect_optional_str(name: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        _die(f"expected '{name}' to be a string when present, got {type(value).__name__}")
    if not value.strip():
        _die(f"expected '{name}' to be a non-empty string when present")
    return value


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fail if status.json is scaffold/stub output."
    )
    p.add_argument(
        "--status",
        required=True,
        help="Path to status.json",
    )
    p.add_argument(
        "--lane-label",
        default="core",
        help="Human-readable lane label for messages (default: core)",
    )
    p.add_argument(
        "--require-detectors-materialized",
        action="store_true",
        help="Also require gates.detectors_materialized_ok == true",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    lane = args.lane_label
    status_path = Path(args.status)

    status = _load_json(status_path)
    gates = _expect_object("gates", status.get("gates"))
    diagnostics = _expect_object("diagnostics", status.get("diagnostics"))

    scaffold = _expect_bool("diagnostics.scaffold", diagnostics.get("scaffold"))
    gates_stubbed = _expect_bool(
        "diagnostics.gates_stubbed", diagnostics.get("gates_stubbed")
    )
    stub_profile = _expect_optional_str(
        "diagnostics.stub_profile", diagnostics.get("stub_profile")
    )

    if scaffold:
        _die(f"{lane} lane must not emit diagnostics.scaffold=true")
    if gates_stubbed:
        _die(f"{lane} lane must not emit diagnostics.gates_stubbed=true")

    det_ok = gates.get("detectors_materialized_ok")
    if args.require_detectors_materialized:
        det_ok = _expect_bool("gates.detectors_materialized_ok", det_ok)
        if det_ok is not True:
            _die(
                f"{lane} lane requires gates.detectors_materialized_ok=true, "
                f"got {det_ok!r}"
            )
    elif det_ok is not None and not isinstance(det_ok, bool):
        _die(
            "expected 'gates.detectors_materialized_ok' to be a boolean "
            f"when present, got {type(det_ok).__name__}"
        )

    print(
        "OK: status is not scaffold/stubbed "
        f"(lane={lane!r}, scaffold={scaffold!r}, "
        f"gates_stubbed={gates_stubbed!r}, "
        f"detectors_materialized_ok={det_ok!r}, "
        f"stub_profile={stub_profile!r})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
