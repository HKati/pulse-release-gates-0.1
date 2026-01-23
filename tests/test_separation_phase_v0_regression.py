#!/usr/bin/env python3
"""
Regression tests for separation_phase_v0 overlay:
- Ensure nested status["results"].* structures are traversed (not treated as flat).
- Ensure contract check fails if required keys are missing (presence != null).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _repo_root() -> Path:
    # tests/ -> repo root
    return Path(__file__).resolve().parents[1]


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


class TestSeparationPhaseV0Regression(unittest.TestCase):
    def test_adapter_recurses_nested_results(self) -> None:
        """
        If status.json uses the common nested layout:
          results.security.<gate_id> = {...}
          results.quality.<gate_id> = {...}
        then the adapter must see those leaf gates.
        We validate this by flipping a nested gate between two runs and expecting it
        to show up in unstable_gates.
        """
        root = _repo_root()

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)

            baseline = {
                "results": {
                    "security": {
                        "gate_security_A": {"status": "PASS"},
                        "gate_security_B": {"status": "PASS"},
                    },
                    "quality": {
                        "gate_quality_X": {"status": "PASS"},
                    },
                    # sometimes there are also top-level booleans in results
                    "external_all_pass": True,
                },
                "decision": "ALLOW",
            }

            # Permuted run flips ONE nested leaf gate
            permuted = {
                "results": {
                    "security": {
                        "gate_security_A": {"status": "PASS"},
                        "gate_security_B": {"status": "FAIL"},  # flip
                    },
                    "quality": {
                        "gate_quality_X": {"status": "PASS"},
                    },
                    "external_all_pass": True,
                },
                "decision": "ALLOW",
            }

            baseline_path = td_path / "status_baseline.json"
            perm_path = td_path / "status_perm_001.json"
            out_path = td_path / "separation_phase_v0.json"

            baseline_path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
            perm_path.write_text(json.dumps(permuted, indent=2) + "\n", encoding="utf-8")

            cmd = [
                sys.executable,
                "scripts/separation_phase_adapter_v0.py",
                "--status",
                str(baseline_path),
                "--permutation-glob",
                str(td_path / "status_perm_*.json"),
                "--out",
                str(out_path),
            ]
            res = _run(cmd, cwd=root)
            self.assertEqual(
                res.returncode,
                0,
                msg=f"adapter failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}",
            )

            data = json.loads(out_path.read_text(encoding="utf-8"))
            inv = data.get("invariants") or {}
            os_ = inv.get("order_stability") or {}

            self.assertEqual(os_.get("method"), "permutations")
            self.assertEqual(os_.get("n_runs"), 2)

            unstable = os_.get("unstable_gates") or []
            self.assertIsInstance(unstable, list)

            # Accept either leaf ids or path-prefixed ids (implementation choice),
            # but we MUST see the flipped gate appear as unstable.
            expected_any = {
                "gate_security_B",
                "security.gate_security_B",
                "results.security.gate_security_B",
            }
            self.assertTrue(
                any(g in expected_any for g in unstable),
                msg=f"Expected flipped nested gate to be unstable; unstable_gates={unstable}",
            )

    def test_contract_rejects_missing_required_keys(self) -> None:
        """
        Contract check must enforce required key presence (missing key != null).
        We generate a valid overlay, then delete required keys and expect failure.
        """
        root = _repo_root()

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)

            baseline = {
                "results": {"security": {"gate_security_A": {"status": "PASS"}}},
                "decision": "ALLOW",
            }

            baseline_path = td_path / "status.json"
            out_path = td_path / "separation_phase_v0.json"
            baseline_path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")

            # 1) generate a valid overlay
            gen = _run(
                [
                    sys.executable,
                    "scripts/separation_phase_adapter_v0.py",
                    "--status",
                    str(baseline_path),
                    "--out",
                    str(out_path),
                ],
                cwd=root,
            )
            self.assertEqual(
                gen.returncode,
                0,
                msg=f"adapter failed:\nSTDOUT:\n{gen.stdout}\nSTDERR:\n{gen.stderr}",
            )

            # 2) contract check should PASS on valid output
            ok = _run(
                [
                    sys.executable,
                    "scripts/check_separation_phase_v0_contract.py",
                    "--in",
                    str(out_path),
                ],
                cwd=root,
            )
            self.assertEqual(
                ok.returncode,
                0,
                msg=f"contract check unexpectedly failed:\nSTDOUT:\n{ok.stdout}\nSTDERR:\n{ok.stderr}",
            )

            # 3) delete required keys -> contract check MUST FAIL
            data = json.loads(out_path.read_text(encoding="utf-8"))

            # Required-by-schema keys we want to enforce presence for:
            # - invariants.order_stability.score
            # - invariants.separation_integrity.decision_stable
            # - invariants.phase_dependency.critical_global_phase
            del data["invariants"]["order_stability"]["score"]
            del data["invariants"]["separation_integrity"]["decision_stable"]
            del data["invariants"]["phase_dependency"]["critical_global_phase"]

            broken_path = td_path / "separation_phase_v0_broken.json"
            broken_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            bad = _run(
                [
                    sys.executable,
                    "scripts/check_separation_phase_v0_contract.py",
                    "--in",
                    str(broken_path),
                ],
                cwd=root,
            )
            self.assertNotEqual(
                bad.returncode,
                0,
                msg="contract check should fail when required keys are missing",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
