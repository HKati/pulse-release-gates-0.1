#!/usr/bin/env python3
"""
Gate Registry Sync Check

Fail if any gate ID present in status.json is missing from pulse_gate_registry_v0.yml.

- Missing in registry: ERROR (exit 2)
- Extra in registry (not seen in this run): WARNING by default (exit 0), or ERROR with --strict-extra

Fail-closed behavior:
- If gate IDs cannot be extracted from status.json (no usable 'gates' or supported nested layout),
  exit with an error to avoid false OK.

Supported status.json layouts for gate IDs:
1) Canonical:
   status["gates"] = { "<gate_id>": true/false/... }

2) Nested (common):
   status["results"]["security|quality|slo|..."]["<gate_id>"] = true/false
   status["results"]["security|quality|..."]["gates"] = { "<gate_id>": ... }
   status["results"]["security|quality|..."]["<gate_id>"] = { "ok": true/false }
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Set, Tuple

import yaml


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: status file not found: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {e}")

    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: expected JSON object at top-level in {path}.")
    return data


def _read_yaml(path: Path) -> Dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        raise SystemExit(f"ERROR: registry file not found: {path}")
    except yaml.YAMLError as e:
        raise SystemExit(f"ERROR: invalid YAML in {path}: {e}")

    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: expected YAML mapping at top-level in {path}.")
    return data


def _as_set_of_keys(d: Dict[str, Any], key: str) -> Set[str]:
    # Fail-closed: required key must exist
    if key not in d:
        raise SystemExit(f"ERROR: missing required key '{key}'.")
    obj = d.get(key) or {}
    if not isinstance(obj, dict):
        raise SystemExit(f"ERROR: expected '{key}' to be a mapping/dict.")
    return set(obj.keys())


def _collect_gate_like_keys(section: Dict[str, Any]) -> Set[str]:
    """
    Collect gate-like keys from a section dict.

    Supports layouts like:
      results.security.<gate_id> = true/false
      results.quality.<gate_id> = {"ok": true/false}
      results.<...>.gates = {<gate_id>: ...}

    This intentionally ignores numeric/string metrics and only pulls:
      - direct boolean leaves
      - dict leaves containing a boolean flag such as ok/pass/passed/value
      - explicit 'gates' mapping keys
    """
    out: Set[str] = set()

    gates_obj = section.get("gates")
    if isinstance(gates_obj, dict):
        out |= set(gates_obj.keys())

    for k, v in section.items():
        if isinstance(v, bool):
            out.add(k)
            continue
        if isinstance(v, dict):
            for flag in ("ok", "pass", "passed", "value"):
                if flag in v and isinstance(v[flag], bool):
                    out.add(k)
                    break

    return out


def _extract_gate_ids_from_status(status: Dict[str, Any]) -> Tuple[Set[str], str]:
    """
    Extract gate IDs from status.json in a fail-closed manner.

    Preferred:
      status["gates"] is a mapping of gate_id -> bool/...
    Fallback (common nested layout):
      status["results"]["security|quality|slo|..."][gate_id] = bool (or {"ok": bool})
      status["results"]["..."]["gates"] = { gate_id: ... }

    Returns:
      (gate_ids, source_string)
    """
    # 1) canonical / preferred
    if "gates" in status:
        gates_obj = status.get("gates")
        if gates_obj is None:
            gates_obj = {}
        if not isinstance(gates_obj, dict):
            raise SystemExit("ERROR: status['gates'] must be a mapping/dict when present.")
        if len(gates_obj) > 0:
            return set(gates_obj.keys()), "status.gates"

    # 2) fallback: results.* sections
    results = status.get("results")
    if isinstance(results, dict):
        out: Set[str] = set()

        # Allowlist: sections that commonly contain gate outcomes
        sections = ("security", "safety", "quality", "slo", "invariants", "sanitization")
        for sec in sections:
            sec_obj = results.get(sec)
            if isinstance(sec_obj, dict):
                out |= _collect_gate_like_keys(sec_obj)

        if out:
            return out, "status.results.(security|quality|...)"

    # 3) fail-closed: cannot determine gate IDs
    raise SystemExit(
        "ERROR: no gate IDs found in status.json. "
        "Expected top-level 'gates' or nested 'results.security/quality/...'. "
        "This would otherwise produce a false OK, so we fail closed."
    )


def _print_stub_block(missing: Set[str]) -> None:
    # Print a YAML fragment the reviewer can paste under `gates:`
    print("\nSuggested registry stubs to paste under `gates:`\n")
    for gid in sorted(missing):
        print(f"  {gid}:")
        print("    category: TODO")
        print('    intent: "TODO: describe what this gate asserts."')
        print("    stability: experimental")
        print("    default_normative: false")
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

    status_gates, source = _extract_gate_ids_from_status(status)
    if source != "status.gates":
        print(f"INFO: extracted gate IDs from {source} (top-level status.gates missing/empty).")

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
