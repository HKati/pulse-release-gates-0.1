#!/usr/bin/env python3
"""
PULSE-REF external summary fixture matrix tests.

These tests execute JSON Schema validation against external_summary_v1 fixture
cases that contain both:

- external_summary.json
- expected_outcome.json

The tests do not define release authority.
They verify that fixture expectations match schema-validation outcomes.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "external_summary_v1"
SUMMARY_SCHEMA_PATH = ROOT / "schemas" / "external_summary_v1.schema.json"


EXPECTED_ACTIVE_FIXTURES = {
    "valid",
    "malformed_missing_tool_version",
    "malformed_missing_subject_digest",
    "malformed_bad_sha256",
    "malformed_empty_metrics",
    "missing_authority_boundary"
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_jsonschema():
    try:
        import jsonschema  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise unittest.SkipTest("jsonschema is not available") from exc

    return jsonschema


def fixture_dirs() -> list[Path]:
    if not FIXTURE_ROOT.exists():
        return []

    dirs: list[Path] = []
    for path in sorted(FIXTURE_ROOT.iterdir()):
        if not path.is_dir():
            continue

        if (path / "external_summary.json").exists() and (path / "expected_outcome.json").exists():
            dirs.append(path)

    return dirs


def error_paths(errors: list[Any]) -> list[list[Any]]:
    return [list(error.path) for error in errors]


class TestExternalSummaryFixtureMatrixV1(unittest.TestCase):
    def setUp(self) -> None:
        self.jsonschema = require_jsonschema()
        self.schema = load_json(SUMMARY_SCHEMA_PATH)
        self.jsonschema.Draft202012Validator.check_schema(self.schema)
        self.validator = self.jsonschema.Draft202012Validator(self.schema)

    def test_expected_active_fixture_set_is_present(self) -> None:
        discovered = {path.name for path in fixture_dirs()}

        self.assertTrue(
            EXPECTED_ACTIVE_FIXTURES.issubset(discovered),
            msg=(
                "Expected all active external summary fixtures to contain both "
                "external_summary.json and expected_outcome.json.\n"
                f"Expected: {sorted(EXPECTED_ACTIVE_FIXTURES)}\n"
                f"Discovered: {sorted(discovered)}"
            ),
        )

    def test_external_summary_fixture_matrix_matches_expected_outcomes(self) -> None:
        fixtures = fixture_dirs()
        self.assertGreaterEqual(
            len(fixtures),
            len(EXPECTED_ACTIVE_FIXTURES),
            "Expected active external_summary_v1 fixtures with external_summary.json and expected_outcome.json.",
        )

        for fixture_dir in fixtures:
            with self.subTest(fixture=fixture_dir.name):
                summary_path = fixture_dir / "external_summary.json"
                expected_path = fixture_dir / "expected_outcome.json"

                summary = load_json(summary_path)
                expected = load_json(expected_path)

                expected_fixture_id = f"external_summary_v1/{fixture_dir.name}"
                self.assertEqual(expected["fixture_id"], expected_fixture_id)
                self.assertEqual(expected["expected_schema"], "schemas/external_summary_v1.schema.json")

                errors = sorted(
                    self.validator.iter_errors(summary),
                    key=lambda error: list(error.path),
                )

                expected_result = expected["expected_result"]

                if expected_result == "PASS":
                    self.assertEqual(
                        errors,
                        [],
                        msg=(
                            "Expected PASS fixture to validate against external_summary_v1 schema.\n"
                            f"Fixture: {summary_path}\n"
                            f"Errors: {[error.message for error in errors]}"
                        ),
                    )

                elif expected_result == "FAIL":
                    self.assertGreater(
                        len(errors),
                        0,
                        msg=(
                            "Expected FAIL fixture to produce schema-validation errors.\n"
                            f"Fixture: {summary_path}"
                        ),
                    )

                    expected_failure = expected.get("expected_failure", {})
                    target_path = expected_failure.get("json_schema_error_path")

                    self.assertIsInstance(
                        target_path,
                        list,
                        msg=(
                            "FAIL fixture must declare expected_failure.json_schema_error_path.\n"
                            f"Fixture: {expected_path}"
                        ),
                    )

                    paths = error_paths(errors)
                    unexpected_paths = [path for path in paths if path != target_path]

                    self.assertEqual(
                        unexpected_paths,
                        [],
                        msg=(
                            "FAIL fixture produced unrelated schema-validation errors. "
                            "Each negative external summary fixture must isolate one expected failure mode.\n"
                            f"Expected path: {target_path!r}\n"
                            f"All paths: {paths!r}\n"
                            f"Messages: {[error.message for error in errors]!r}"
                        ),
                    )

                    missing_property = expected_failure.get("missing_property")
                    if missing_property:
                        self.assertTrue(
                            any(missing_property in error.message for error in errors),
                            msg=(
                                "Expected schema errors to mention the missing property.\n"
                                f"Missing property: {missing_property!r}\n"
                                f"Messages: {[error.message for error in errors]!r}"
                            ),
                        )

                    invalid_value = expected_failure.get("invalid_value")
                    if invalid_value is not None:
                        self.assertTrue(
                            errors,
                            msg="Expected invalid-value fixture to produce at least one schema error.",
                        )

                else:
                    self.fail(f"Unsupported expected_result: {expected_result!r}")

                self.assertIn("authority_boundary", expected)
                self.assertIn(
                    "does not define release authority",
                    expected["authority_boundary"],
                )

    def test_expected_outcome_metadata_has_authority_boundary(self) -> None:
        fixtures = fixture_dirs()
        self.assertGreaterEqual(len(fixtures), len(EXPECTED_ACTIVE_FIXTURES))

        for fixture_dir in fixtures:
            with self.subTest(fixture=fixture_dir.name):
                expected = load_json(fixture_dir / "expected_outcome.json")

                self.assertIn("authority_boundary", expected)
                self.assertIn(
                    "does not define release authority",
                    expected["authority_boundary"],
                )


if __name__ == "__main__":
    unittest.main()
