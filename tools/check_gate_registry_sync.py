#!/usr/bin/env python3
"""
Gate Registry Sync Check

Fail if any gate ID present in status.json is missing from pulse_gate_registry_v0.yml.

- Missing in registry: ERROR (exit 2)
- Extra in registry (not seen in this run): WARNING by default (exit 0)

Optional: print YAML stubs for missing gates to speed up registry updates.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Set

import yaml


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: status file not found: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {e}")


def _read_yaml(path: Path) -> Dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        raise SystemExit(f"ERROR: registry file not found: {path}")
    except yaml.YAMLError as e:
        raise SystemExit(f"ERROR: invalid YAML in {path}: {e}")


def _as_set_of_keys(d: Dict[str, Any], key: str) -> Set[str]:
    obj = d.get(key, {}) or {}
    if not isinstance(obj, dict):
        raise SystemExit(f"ERROR: expected '{key}' to be a mapping/dict.")
    return set(obj.keys())


def _print_stub_block(missing: Set[str]) -> None:
    # Print a YAML fragment the reviewer can paste under `gates:`
    print("\nSuggested registry stubs to paste under `gates:`\n")
    for gid in sorted(missing):
        print(f"  {gid}:")
        print(f"    category: TODO")
        print(f"    intent: \"TODO: describe what this gate asserts.\"")
        print(f"    stability: experimental")
        print(f"    default_normative: false")
        print("")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", default="artifacts/status.json", help="Path to status.json")
    ap.add_argument("--registry", default="pulse_gate_registry_v0.yml", help="Path to gate registry YAML")
    ap.add_argument(
        "--strict-extra",
        action="store_true",
        help="Treat gates present in registry but not seen in this status run as an error.",
    )
    ap.add_argument(
        "--emit-stubs",
        action="store_true",
        help="If missing gates are found, print YAML stubs to help update the registry.",
    )
    args = ap.parse_args()

    status_path = Path(args.status)
    registry_path = Path(args.registry)

    status = _read_json(status_path)
    registry = _read_yaml(registry_path)

    status_gates = _as_set_of_keys(status, "gates")
    registry_gates = _as_set_of_keys(registry, "gates")

    missing_in_registry = status_gates - registry_gates
    extra_in_registry = registry_gates - status_gates

    if missing_in_registry:
        print("ERROR: gate IDs present in status.json but missing in registry:")
        for g in sorted(missing_in_registry):
            print(f"  - {g}")
        if args.emit_stubs:
            _print_stub_block(missing_in_registry)
        return 2

    if extra_in_registry:
        msg = "ERROR" if args.strict_extra else "WARN"
        print(f"{msg}: gate IDs present in registry but not seen in this status run:")
        for g in sorted(extra_in_registry):
            print(f"  - {g}")
        if args.strict_extra:
            return 3

    print("OK: gate registry covers all gate IDs seen in status.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
