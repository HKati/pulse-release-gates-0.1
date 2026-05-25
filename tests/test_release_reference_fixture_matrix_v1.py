#!/usr/bin/env python3
"""
PULSE-REF release reference fixture matrix tests.

These tests execute the PULSE-REF release reference completeness guard against
fixture cases that contain both:

- status.json
- expected_outcome.json

The tests do not define release authority.
They verify that fixture expectations match the guard outcome.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "release_reference_v1"
GUARD = ROOT / "ci" / "check_release_reference_complete_v1.py"
POLICY = ROOT / "pulse_gate_policy_v0.yml"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_dirs() -> list[Path]:
    if not FIXTURE_ROOT.exists():
        return []

    dirs: list[Path] = []
    for path in sorted(FIXTURE_ROOT.iterdir()):
        if not path.is_dir():
            continue

        if (path / "status.json").exists() and (path / "expected_outcome.json").exists():
            dirs.append(path)

    return dirs


def extract_guard_errors(output: str) -> list[str]:
    """Extract bullet error lines emitted by the PULSE-REF guard."""
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


def expected_extra_required_gates(expected: dict[str, Any]) -> list[str]:
    """Return additional fixture-specific release-grade gates."""
    gates = expected.get("expected_extra_required_gates", [])
    if gates is None:
        return []

    if not isinstance(gates, list):
        raise TypeError("expected_extra_required_gates must be a list when present.")

    out: list[str] = []
    for gate in gates:
        if not isinstance(gate, str) or not gate:
            raise TypeError("expected_extra_required_gates entries must be non-empty strings.")
        out.append(gate)

    return out


class TestReleaseReferenceFixtureMatrixV1(unittest.TestCase):
    def test_fixture_matrix_matches_expected_guard_outcomes(self) -> None:
        fixtures = fixture_dirs()
        self.assertGreaterEqual(
            len(fixtures),
            1,
            "Expected at least one release reference fixture with status.json and expected_outcome.json.",
        )

        for fixture_dir in fixtures:
            with self.subTest(fixture=fixture_dir.name):
                status_path = fixture_dir / "status.json"
                expected_path = fixture_dir / "expected_outcome.json"

                status = load_json(status_path)
                expected = load_json(expected_path)

                expected_fixture_id = f"release_reference_v1/{fixture_dir.name}"
                self.assertEqual(expected["fixture_id"], expected_fixture_id)

                cmd = [
                    sys.executable,
                    str(GUARD.relative_to(ROOT)),
                    "--status",
                    str(status_path.relative_to(ROOT)),
                    "--policy",
                    str(POLICY.relative_to(ROOT)),
                    "--required-sets",
                    "required,release_required",
                    "--allowed-run-modes",
                    "prod",
                    "--require-nonstubbed",
                    "--require-nonscaffolded",
                    "--require-detectors-materialized",
                    "--require-external-summaries",
                ]

                for gate in expected_extra_required_gates(expected):
                    cmd.extend(["--require-gate", gate])

                proc = subprocess.run(
                    cmd,
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )

                output = proc.stdout + proc.stderr
                expected_result = expected["expected_result"]

                if expected_result == "PASS":
                    self.assertEqual(
                        proc.returncode,
                        0,
                        msg=f"Expected PASS fixture to pass guard.\nOutput:\n{output}",
                    )
                    self.assertIn("Result: PASS", output)

                elif expected_result == "FAIL":
                    self.assertNotEqual(
                        proc.returncode,
                        0,
                        msg=f"Expected FAIL fixture to fail guard.\nOutput:\n{output}",
                    )
                    self.assertIn("Result: FAIL", output)

                    expected_failure = expected.get("expected_failure", {})
                    target = expected_failure.get("gate") or expected_failure.get("field")

                    self.assertIsInstance(
                        target,
                        str,
                        msg=(
                            "FAIL fixture must declare expected_failure.gate "
                            f"or expected_failure.field: {expected_path}"
                        ),
                    )
                    self.assertTrue(
                        target,
                        msg=f"FAIL fixture expected failure target must be non-empty: {expected_path}",
                    )

                    errors = extract_guard_errors(output)
                    self.assertGreater(
                        len(errors),
                        0,
                        msg=f"Expected guard output to include structured error lines.\nOutput:\n{output}",
                    )

                    matching_errors = [error for error in errors if target in error]
                    unexpected_errors = [error for error in errors if target not in error]

                    self.assertGreater(
                        len(matching_errors),
                        0,
                        msg=(
                            "Expected guard errors to mention the intended failing gate/field "
                            f"{target!r}.\nErrors:\n{errors}\nOutput:\n{output}"
                        ),
                    )

                    self.assertEqual(
                        unexpected_errors,
                        [],
                        msg=(
                            "FAIL fixture produced unrelated guard errors. "
                            "Each negative fixture must isolate one expected failure mode.\n"
                            f"Expected target: {target!r}\n"
                            f"Unexpected errors: {unexpected_errors}\n"
                            f"All errors: {errors}\n"
                            f"Output:\n{output}"
                        ),
                    )

                else:
                    self.fail(f"Unsupported expected_result: {expected_result!r}")

                self.assertIn("gates", status)
                self.assertIn("authority_boundary", expected)
                self.assertIn("does not define release authority", expected["authority_boundary"])

    def test_expected_outcome_metadata_has_authority_boundary(self) -> None:
        fixtures = fixture_dirs()
        self.assertGreaterEqual(len(fixtures), 1)

        for fixture_dir in fixtures:
            with self.subTest(fixture=fixture_dir.name):
                expected = load_json(fixture_dir / "expected_outcome.json")

                self.assertIn("authority_boundary", expected)
                self.assertIn(
                    "does not define release authority",
                    expected["authority_boundary"],
                )
                self.assertEqual(
                    expected["expected_guard"],
                    "ci/check_release_reference_complete_v1.py",
                )


if __name__ == "__main__":
    unittest.main()
