import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_no_stub_release.py"
FIXTURES = ROOT / "tests" / "fixtures" / "no_stub_release_boundary"


class NoStubReleaseBoundaryTests(unittest.TestCase):
    def run_check_path(self, status_path: Path, lane: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(TOOL),
                str(status_path),
                "--lane",
                lane,
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def run_check(self, fixture_name: str, lane: str) -> subprocess.CompletedProcess:
        path = FIXTURES / fixture_name
        self.assertTrue(path.exists(), f"missing fixture: {path}")
        return self.run_check_path(path, lane)

    def run_check_status(self, status: dict, lane: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as temp_dir:
            status_path = Path(temp_dir) / "status.json"
            status_path.write_text(
                json.dumps(status, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            return self.run_check_path(status_path, lane)

    def assert_passed(self, result: subprocess.CompletedProcess) -> None:
        self.assertEqual(
            result.returncode,
            0,
            msg=f"expected PASS\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("PASS", result.stdout)

    def assert_failed(self, result: subprocess.CompletedProcess) -> None:
        self.assertNotEqual(
            result.returncode,
            0,
            msg=f"expected FAIL\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("FAIL", result.stderr)

    def test_core_scaffold_allowed_for_core_lane(self):
        result = self.run_check("core_scaffold_allowed.json", "core")

        self.assert_passed(result)

    def test_release_scaffold_forbidden_for_release_grade_lane(self):
        result = self.run_check("release_scaffold_forbidden.json", "release-grade")

        self.assert_failed(result)
        self.assertTrue(
            "stub" in result.stderr.lower()
            or "scaffold" in result.stderr.lower()
            or "smoke" in result.stderr.lower(),
            msg=result.stderr,
        )

    def test_release_missing_diagnostics_forbidden(self):
        result = self.run_check(
            "release_missing_diagnostics_forbidden.json",
            "release-grade",
        )

        self.assert_failed(result)
        self.assertIn("diagnostics", result.stderr.lower())

    def test_release_missing_materialization_forbidden(self):
        result = self.run_check(
            "release_missing_materialization_forbidden.json",
            "release-grade",
        )

        self.assert_failed(result)
        self.assertIn("detectors_materialized_ok", result.stderr)

    def test_release_real_evidence_allowed_for_release_grade_lane(self):
        result = self.run_check("release_real_evidence_allowed.json", "release-grade")

        self.assert_passed(result)

    def test_release_real_evidence_allowed_for_prod_lane(self):
        result = self.run_check("release_real_evidence_allowed.json", "prod")

        self.assert_passed(result)

    def test_unknown_status_run_mode_fails_closed_for_prod_lane(self):
        status = {
            "version": "test",
            "created_utc": "2026-04-25T00:00:00Z",
            "gates": {
                "q1_grounded_ok": True,
                "q4_slo_ok": True,
                "detectors_materialized_ok": True,
                "external_summaries_present": True,
                "external_all_pass": True,
            },
            "metrics": {
                "run_mode": "shadow",
            },
            "diagnostics": {
                "gates_stubbed": False,
                "scaffold": False,
                "stub_profile": "materialized_evidence",
            },
        }

        result = self.run_check_status(status, "prod")

        self.assert_failed(result)
        self.assertIn("run_mode", result.stderr)

    def test_conflicting_diagnostic_sources_fail_closed(self):
        status = {
            "version": "test",
            "created_utc": "2026-04-25T00:00:00Z",
            "gates": {
                "q1_grounded_ok": True,
                "q4_slo_ok": True,
                "detectors_materialized_ok": True,
                "external_summaries_present": True,
                "external_all_pass": True,
            },
            "metrics": {
                "run_mode": "prod",
            },
            "meta": {
                "diagnostics": {
                    "gates_stubbed": True,
                    "scaffold": True,
                    "stub_profile": "all_true_smoke",
                },
            },
            "diagnostics": {
                "gates_stubbed": False,
                "scaffold": False,
                "stub_profile": "materialized_evidence",
            },
        }

        result = self.run_check_status(status, "prod")

        self.assert_failed(result)
        self.assertTrue(
            "conflicting" in result.stderr.lower()
            or "meta.diagnostics" in result.stderr.lower()
            or "stub" in result.stderr.lower()
            or "scaffold" in result.stderr.lower(),
            msg=result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
