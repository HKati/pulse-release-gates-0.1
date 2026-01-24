#!/usr/bin/env python3
"""
Governance tools smoke tests.

Goal: ensure repo-level governance checks run in CI without depending on the PULSE pack.
These are intentionally lightweight and deterministic.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    subprocess.check_call(cmd, cwd=str(ROOT))


def test_gate_registry_sync_smoke() -> None:
    """
    Smoke test: check_gate_registry_sync should succeed when registry covers all gates in a status.json fixture.
    """
    tmp = ROOT / "tests" / "out"
    tmp.mkdir(parents=True, exist_ok=True)

    status_path = tmp / "status_fixture.json"
    registry_path = ROOT / "pulse_gate_registry_v0.yml"

    # Minimal status fixture: include a few representative gates that should exist in registry
    status = {
        "gates": {
            "q1_grounded_ok": True,
            "q4_slo_ok": True,
            "psf_monotonicity_ok": True,
            "external_all_pass": True,
            "refusal_delta_pass": True,
        },
        "metrics": {},
    }
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")

    run(
        [
            sys.executable,
            "tools/check_gate_registry_sync.py",
            "--status",
            str(status_path),
            "--registry",
            str(registry_path),
        ]
    )


def test_policy_registry_consistency_smoke() -> None:
    """
    Smoke test: policy↔registry consistency check should pass for the repo defaults.
    """
    run(
        [
            sys.executable,
            "tools/tools/check_policy_registry_consistency.py",
            "--registry",
            "pulse_gate_registry_v0.yml",
            "--policy",
            "pulse_gate_policy_v0.yml",
            "--sets",
            "required",
        ]
    )
