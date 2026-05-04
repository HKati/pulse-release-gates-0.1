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
                    "--require-detectors-materialized",
                    "--require-external-summaries",
                ]

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
                            "Expected FAIL fixtures to set expected_failure.gate or "
                            f"expected_failure.field.\nFixture: {fixture_dir.name}"
                        ),
                    )
                    self.assertTrue(
                        target,
                        msg=(
                            "Expected FAIL fixtures to set a non-empty expected_failure.gate or "
                            f"expected_failure.field.\nFixture: {fixture_dir.name}"
                        ),
                    )

                    errors = extract_guard_errors(output)
                    self.assertGreater(
                        len(errors),
                        0,
                        msg=f"Expected FAIL guard output to include Errors entries.\nOutput:\n{output}",
                    )

                    matching_errors = [error for error in errors if target in error]
                    unexpected_errors = [error for error in errors if target not in error]

                    self.assertGreater(
                        len(matching_errors),
                        0,
                        msg=(
                            "Expected at least one guard error to mention the intended failing "
                            f"target {target!r}.\nErrors:\n" + "\n".join(errors)
                        ),
                    )
                    self.assertEqual(
                        unexpected_errors,
                        [],
                        msg=(
                            "Expected FAIL fixture guard errors to be isolated to the intended "
                            f"target {target!r}, but found unrelated errors:\n"
                            + "\n".join(unexpected_errors)
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
