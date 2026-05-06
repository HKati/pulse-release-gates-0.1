#!/usr/bin/env python3
"""
PULSE-REF no-implicit-PASS release-grade tests.

These tests verify that release-grade validation does not infer PASS from
missing materialized evidence.

The tests do not define release authority.
They exercise the PULSE-REF completeness guard against fixture evidence.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "ci" / "check_release_reference_complete_v1.py"
POLICY = ROOT / "pulse_gate_policy_v0.yml"
FIXTURE = ROOT / "tests" / "fixtures" / "release_reference_v1" / "missing_refusal_delta"
STATUS = FIXTURE / "status.json"
EXPECTED = FIXTURE / "expected_outcome.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_guard_errors(output: str) -> list[str]:
    errors: list[str] = []
    in_errors = False

    for raw_line in output.splitlines():
        line = raw_line.strip()

        if line == "Errors:":
            in_errors = True
            continue

        if in_errors and line.startswith("Result:"):
            break

        if in_errors and line.startswith("- "):
            errors.append(line[2:])

    return errors


class TestNoImplicitPassReleaseGrade(unittest.TestCase):
    def test_missing_refusal_delta_evidence_fails_release_grade_validation(self) -> None:
        status = load_json(STATUS)
        expected = load_json(EXPECTED)

        self.assertEqual(expected["fixture_id"], "release_reference_v1/missing_refusal_delta")
        self.assertEqual(expected["expected_result"], "FAIL")
        self.assertEqual(expected["expected_guard"], "ci/check_release_reference_complete_v1.py")
        self.assertIn("refusal_delta_evidence_present", expected["expected_extra_required_gates"])

        self.assertEqual(status["metrics"]["run_mode"], "prod")
        self.assertFalse(status["diagnostics"]["gates_stubbed"])
        self.assertTrue(status["gates"]["refusal_delta_pass"])
        self.assertFalse(status["gates"]["refusal_delta_evidence_present"])

        cmd = [
            sys.executable,
            str(GUARD.relative_to(ROOT)),
            "--status",
            str(STATUS.relative_to(ROOT)),
            "--policy",
            str(POLICY.relative_to(ROOT)),
            "--required-sets",
            "required,release_required",
            "--allowed-run-modes",
            "prod",
            "--require-nonstubbed",
            "--require-detectors-materialized",
            "--require-external-summaries",
            "--require-gate",
            "refusal_delta_evidence_present"
        ]

        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        output = proc.stdout + proc.stderr

        self.assertNotEqual(
            proc.returncode,
            0,
            msg=f"Expected missing refusal-delta evidence fixture to fail.\nOutput:\n{output}",
        )
        self.assertIn("Result: FAIL", output)

        errors = extract_guard_errors(output)
        self.assertGreater(
            len(errors),
            0,
            msg=f"Expected guard output to include structured error lines.\nOutput:\n{output}",
        )

        target = "refusal_delta_evidence_present"
        matching_errors = [error for error in errors if target in error]
        unrelated_errors = [error for error in errors if target not in error]

        self.assertGreater(
            len(matching_errors),
            0,
            msg=(
                "Expected guard errors to mention refusal_delta_evidence_present.\n"
                f"Errors:\n{errors}\nOutput:\n{output}"
            ),
        )

        self.assertEqual(
            unrelated_errors,
            [],
            msg=(
                "Missing refusal-delta evidence fixture produced unrelated guard errors.\n"
                f"Expected target: {target!r}\n"
                f"Unexpected errors: {unrelated_errors}\n"
                f"All errors: {errors}\n"
                f"Output:\n{output}"
            ),
        )

    def test_fixture_metadata_preserves_authority_boundary(self) -> None:
        expected = load_json(EXPECTED)

        self.assertIn("authority_boundary", expected)
        self.assertIn("does not define release authority", expected["authority_boundary"])


if __name__ == "__main__":
    unittest.main()
