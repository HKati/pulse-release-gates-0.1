#!/usr/bin/env python3
"""
CI pack-layout preflight for PULSE_safe_pack_v0.

Purpose:
- Fail early if critical files/scripts referenced by the CI "critical path" are missing.
- On release-grade runs (tags or strict workflow_dispatch), enforce additional required artifacts
  and refusal-delta pairs source presence (fail-closed).
- For non-critical/reporting scripts, emit warnings only.

This reduces pack-layout drift and prevents silent skips.
"""

from __future__ import annotations

import argparse
import pathlib
import sys


def _gh_error(msg: str) -> None:
    print(f"::error::{msg}")


def _gh_warn(msg: str) -> None:
    print(f"::warning::{msg}")


def _check_exists(path: pathlib.Path, *, required: bool, label: str) -> bool:
    if path.exists():
        return True
    if required:
        _gh_error(f"Missing required {label}: {path}")
        return False
    _gh_warn(f"Missing optional {label}: {path}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--pack_dir", default="PULSE_safe_pack_v0", help="Path to PULSE safe-pack directory")
    ap.add_argument("--release-grade", action="store_true", help="Fail-closed on release-grade requirements")
    args = ap.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    pack_dir = pathlib.Path(args.pack_dir)
    if not pack_dir.is_absolute():
        pack_dir = repo_root / pack_dir

    ok = True

    # ---------------------------------------------------------------------
    # Always-required: critical path inputs/tools (must exist on all runs)
    # ---------------------------------------------------------------------
    always_required = [
        repo_root / "pulse_gate_policy_v0.yml",
        repo_root / "pulse_gate_registry_v0.yml",
        repo_root / "schemas" / "status" / "status_v1.schema.json",
        repo_root / "tools" / "policy_to_require_args.py",
        repo_root / "tools" / "check_gate_registry_sync.py",
        repo_root / "tools" / "tools" / "check_policy_registry_consistency.py",
        repo_root / "scripts" / "check_external_summaries_present.py",
        pack_dir / "tools" / "run_all.py",
        pack_dir / "tools" / "augment_status.py",
        pack_dir / "tools" / "check_gates.py",
        pack_dir / "profiles" / "external_thresholds.yaml",
    ]

    for p in always_required:
        ok = _check_exists(p, required=True, label="critical file/tool") and ok

    # ---------------------------------------------------------------------
    # Release-grade required: must exist when tags/strict runs are used
    # ---------------------------------------------------------------------
    release_required = [
        pack_dir / "tools" / "refusal_delta.py",
        pack_dir / "profiles" / "pulse_policy.yaml",
    ]

    if args.release_grade:
        for p in release_required:
            ok = _check_exists(p, required=True, label="release-grade file/tool") and ok

        # Refusal-delta must have at least one pairs source:
        # - policy_to_refusal_pairs.py + policy OR a shipped pairs file
        pairs_script = pack_dir / "tools" / "policy_to_refusal_pairs.py"
        pairs_file = pack_dir / "examples" / "refusal_pairs.jsonl"
        policy_file = repo_root / "pulse_gate_policy_v0.yml"

        have_pairs_source = False
        if pairs_script.exists() and policy_file.exists():
            have_pairs_source = True
        if pairs_file.exists():
            have_pairs_source = True

        if not have_pairs_source:
            _gh_error(
                "Release-grade refusal-delta requires a pairs source, but none was found. "
                f"Expected either {pairs_script} + {policy_file} or {pairs_file}."
            )
            ok = False

    # ---------------------------------------------------------------------
    # Optional/reporting tools: warn only (visibility without breaking CI)
    # ---------------------------------------------------------------------
    optional = [
        pack_dir / "tools" / "status_to_summary.py",
        pack_dir / "tools" / "update_artifacts_for_snapshot.py",
    ]
    for p in optional:
        _check_exists(p, required=False, label="reporting tool")

    if ok:
        print(
            "OK: pack-layout preflight passed "
            f"(pack_dir={pack_dir}, release_grade={bool(args.release_grade)})"
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
