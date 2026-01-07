
# tests/test_pages_publish_paradox_core_bundle_v0.py
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _run(cmd, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """
    Run a command and capture stdout/stderr for deterministic debugging.
    We do not use shell=True and we do not rely on wall-clock timestamps.
    """
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )


def _check_ok(cmd, cwd: Path | None = None) -> None:
    proc = _run(cmd, cwd=cwd)
    if proc.returncode != 0:
        raise AssertionError(
            "Command failed (expected success)\n"
            f"cmd: {cmd}\n"
            f"returncode: {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
        )


class TestPagesPublishParadoxCoreBundleV0(unittest.TestCase):
    def test_mount_contract_rejects_path_traversal(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]

        fixture_field = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "field_v0.json"
        fixture_edges = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "edges_v0.jsonl"

        bundle_tool = repo_root / "scripts" / "paradox_core_reviewer_bundle_v0.py"
        publish_tool = repo_root / "scripts" / "pages_publish_paradox_core_bundle_v0.py"

        self.assertTrue(fixture_field.exists(), f"Missing fixture field: {fixture_field}")
        self.assertTrue(fixture_edges.exists(), f"Missing fixture edges: {fixture_edges}")
        self.assertTrue(bundle_tool.exists(), f"Missing bundle tool: {bundle_tool}")
        self.assertTrue(publish_tool.exists(), f"Missing pages publish tool: {publish_tool}")

        with tempfile.TemporaryDirectory(prefix="pulse_test_pages_publish_") as td:
            td = Path(td)
            bundle_dir = td / "bundle"
            site_dir = td / "site"

            # 1) Build a deterministic reviewer bundle from fixtures.
            _check_ok(
                [
                    sys.executable,
                    str(bundle_tool),
                    "--field",
                    str(fixture_field),
                    "--edges",
                    str(fixture_edges),
                    "--out-dir",
                    str(bundle_dir),
                    "--k",
                    "2",
                    "--metric",
                    "severity",
                ]
            )

            # 2) Publish into a safe mount (should succeed).
            _check_ok(
                [
                    sys.executable,
                    str(publish_tool),
                    "--bundle-dir",
                    str(bundle_dir),
                    "--site-dir",
                    str(site_dir),
                    "--mount",
                    "paradox/core/v0",
                ]
            )

            mounted = site_dir / "paradox" / "core" / "v0"
            self.assertTrue(mounted.exists(), f"Expected mount dir to exist: {mounted}")

            # Expect at least one known artifact in the mount directory.
            # (We don't hardcode the full list here; we only need evidence of publish.)
            expected_any = ["paradox_core_v0.json", "paradox_core_summary_v0.md", "paradox_core_k2.svg", "index.html"]
            self.assertTrue(
                any((mounted / name).exists() for name in expected_any),
                f"Expected at least one known artifact under mount. Found: {[p.name for p in mounted.glob('*')]}",
            )

            # 3) Path traversal attempts must fail-closed.
            bad_mounts = [
                "../evil",
                "../../evil",
                "paradox/../evil",
                "paradox/core/v0/../../evil",
                "paradox/core/v0/../..",
            ]

            for bad in bad_mounts:
                proc = _run(
                    [
                        sys.executable,
                        str(publish_tool),
                        "--bundle-dir",
                        str(bundle_dir),
                        "--site-dir",
                        str(site_dir),
                        "--mount",
                        bad,
                    ]
                )
                self.assertNotEqual(
                    proc.returncode,
                    0,
                    "Bad mount unexpectedly succeeded (must fail-closed)\n"
                    f"mount: {bad}\n"
                    f"stdout:\n{proc.stdout}\n"
                    f"stderr:\n{proc.stderr}\n",
                )


if __name__ == "__main__":
    unittest.main()
