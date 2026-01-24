#!/usr/bin/env python3
"""
Policy ↔ Gate Registry consistency check (fail-closed).

What it enforces:
- Every gate ID referenced by a policy set (default: required) must exist in
  pulse_gate_registry_v0.yml under `gates:`.
- Policy must not require gates that are marked non-normative by default
  (`default_normative: false`) unless explicitly allowlisted.

Rationale:
- Gate IDs are stable core. Policy is a projection of measured state.
- Diagnostic/shadow gates must not silently become normative due to policy drift.

This is a governance/engineering guardrail: it prevents meaning drift and
accidental promotion of diagnostic signals into CI outcomes.

Exit codes:
- 0: OK
- 2: Consistency violation (fail-closed)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml


def _gh_error(msg: str) -> None:
    # GitHub Actions-friendly annotation
    print(f"::error::{msg}")


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        _gh_error(f"YAML not found: {path}")
        sys.exit(2)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        _gh_error(f"Failed to parse YAML: {path} ({e})")
        sys.exit(2)
    if not isinstance(data, dict):
        _gh_error(f"YAML root must be a mapping/object: {path}")
        sys.exit(2)
    return data


def _repo_root() -> Path:
    """
    Resolve repo root robustly even if this file ends up nested (e.g. tools/tools/).

    Strategy:
    - Walk upwards from this file's directory.
    - Prefer a directory containing .git.
    - Fallback to a directory containing both pulse_gate_policy_v0.yml and
      pulse_gate_registry_v0.yml.
    """
    here = Path(__file__).resolve()

    for parent in here.parents:
        # Standard git checkout (most CI + local dev)
        if (parent / ".git").exists():
            return parent

        # Repo-export / tarball / environments without .git
        if (parent / "pulse_gate_policy_v0.yml").exists() and (parent / "pulse_gate_registry_v0.yml").exists():
            return parent

    # Very conservative fallback: assume two levels up from tools/tools/...
    # (kept only as last resort)
    if len(here.parents) >= 3:
        return here.parents[2]
    return here.parent


def _policy_to_gate_ids(policy_path: Path, set_name: str) -> List[str]:
    """
    Use the repo's canonical parser for policy sets (policy_to_require_args.py),
    so we don't duplicate policy semantics here.
    """
    root = _repo_root()
    helper = root / "tools" / "policy_to_require_args.py"
    if not helper.exists():
        _gh_error(f"Missing helper: {helper} (expected policy_to_require_args.py)")
        sys.exit(2)

    cmd = [sys.executable, str(helper), "--policy", str(policy_path), "--set", set_name]
    try:
        out = subprocess.check_output(cmd, text=True, cwd=str(root)).strip()
    except subprocess.CalledProcessError as e:
        _gh_error(f"Failed to extract gates from policy set '{set_name}': {e}")
        _gh_error("Tip: verify pulse_gate_policy_v0.yml format and the requested set name.")
        sys.exit(2)

    # policy_to_require_args.py is expected to output a whitespace-separated list of gate IDs
    toks = [t.strip() for t in out.split() if t.strip()]

    # Defensive filter: keep only plausible gate IDs
    gate_re = re.compile(r"^[A-Za-z0-9_]+$")
    gates = [t for t in toks if gate_re.match(t)]

    if not gates:
        _gh_error(
            f"Policy set '{set_name}' resolved to an empty gate list. "
            "Failing closed (this likely indicates a policy parse or definition issue)."
        )
        sys.exit(2)

    return gates


def _gate_entry(registry: Dict[str, Any], gate_id: str) -> Dict[str, Any]:
    gates = registry.get("gates", {})
    if not isinstance(gates, dict):
        _gh_error("Registry YAML must contain a top-level mapping `gates:`")
        sys.exit(2)
    entry = gates.get(gate_id)
    if entry is None:
        return {}
    if not isinstance(entry, dict):
        # treat malformed as missing/invalid
        return {}
    return entry


def _is_default_normative(entry: Dict[str, Any]) -> bool:
    # By default gates are normative unless explicitly marked otherwise.
    v = entry.get("default_normative", True)
    return bool(v)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True, help="Path to pulse_gate_registry_v0.yml")
    ap.add_argument(
        "--policy",
        default=None,
        help="Path to policy YAML (e.g., pulse_gate_policy_v0.yml). If set, use --sets.",
    )
    ap.add_argument(
        "--sets",
        nargs="+",
        default=["required"],
        help="Policy sets to check (default: required).",
    )
    ap.add_argument(
        "--gates",
        nargs="+",
        default=None,
        help="Explicit gate IDs to check (useful for workflows with inline REQ lists).",
    )
    ap.add_argument(
        "--allow-non-normative",
        nargs="*",
        default=[],
        help="Allowlist of gate IDs permitted even if default_normative=false (escape hatch).",
    )
    args = ap.parse_args()

    root = _repo_root()
    registry_path = Path(args.registry)
    if not registry_path.is_absolute():
        registry_path = (root / registry_path).resolve()

    registry = _read_yaml(registry_path)

    allow_non_norm = set(args.allow_non_normative or [])

    # Build the check set
    source_desc = ""
    check_gates: List[str] = []

    if args.gates:
        check_gates = list(args.gates)
        source_desc = "explicit --gates list"
    else:
        if not args.policy:
            _gh_error("Either --gates or --policy must be provided.")
            sys.exit(2)

        policy_path = Path(args.policy)
        if not policy_path.is_absolute():
            policy_path = (root / policy_path).resolve()

        # Extract per-set gates and union them (but keep set-aware reporting)
        per_set: Dict[str, List[str]] = {}
        for s in args.sets:
            per_set[s] = _policy_to_gate_ids(policy_path, s)

        # Flatten (preserve order but unique)
        seen: Set[str] = set()
        for s in args.sets:
            for g in per_set[s]:
                if g not in seen:
                    check_gates.append(g)
                    seen.add(g)

        source_desc = f"policy={policy_path.name} sets={args.sets}"

    missing: Set[str] = set()
    non_normative: Set[str] = set()

    for gid in check_gates:
        entry = _gate_entry(registry, gid)
        if not entry:
            missing.add(gid)
            continue

        if not _is_default_normative(entry) and gid not in allow_non_norm:
            non_normative.add(gid)

    if missing or non_normative:
        _gh_error(f"Policy/required gate consistency check failed ({source_desc}).")

        if missing:
            _gh_error("Gate IDs referenced by policy/workflow but missing in registry:")
            for gid in sorted(missing):
                _gh_error(f"- {gid}")

        if non_normative:
            _gh_error("Non-normative gates (default_normative: false) are being required:")
            for gid in sorted(non_normative):
                _gh_error(f"- {gid}")
            _gh_error(
                "Fix: remove them from required sets, or intentionally promote via a new gate ID "
                "(do not repurpose existing IDs)."
            )

        sys.exit(2)

    print(f"OK: policy/required gates are registry-backed and normative ({source_desc}).")


if __name__ == "__main__":
    main()
