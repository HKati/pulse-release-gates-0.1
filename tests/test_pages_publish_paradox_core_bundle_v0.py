from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True)


def _run_ok(cmd: list[str]) -> None:
    r = _run(cmd)
    assert r.returncode == 0, (
        f"Command failed:\n{' '.join(cmd)}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    )


def test_pages_publish_mount_contract_rejects_traversal(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    py = sys.executable

    bundle_tool = repo_root / "scripts" / "paradox_core_reviewer_bundle_v0.py"
    publish_tool = repo_root / "scripts" / "pages_publish_paradox_core_bundle_v0.py"

    field = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "field_v0.json"
    edges = repo_root / "tests" / "fixtures" / "paradox_core_projection_v0" / "edges_v0.jsonl"

    bundle_dir = tmp_path / "bundle"
    site_dir = tmp_path / "site"

    # Build deterministic bundle (fixtures, k=2)
    _run_ok(
        [
            py,
            str(bundle_tool),
            "--field",
            str(field),
            "--edges",
            str(edges),
            "--out-dir",
            str(bundle_dir),
            "--k",
            "2",
            "--metric",
            "severity",
        ]
    )

    # Publish to a safe mount (must succeed)
    _run_ok(
        [
            py,
            str(publish_tool),
            "--bundle-dir",
            str(bundle_dir),
            "--site-dir",
            str(site_dir),
            "--mount",
            "paradox/core/v0",
            "--write-index",
        ]
    )

    mounted = site_dir / "paradox" / "core" / "v0"
    assert mounted.exists()

    # Required published outputs (contract)
    required = [
        "paradox_core_v0.json",
        "paradox_core_summary_v0.md",
        "paradox_core_v0.svg",
        "paradox_core_reviewer_card_v0.html",
        "index.html",
    ]
    for name in required:
        assert (mounted / name).exists(), f"Missing published file: {name}"

    # Path traversal / invalid mounts must fail-closed
    bad_mounts = [
        "../evil",
        "../../evil",
        "paradox/../evil",
        "paradox/core/v0/../../evil",
        "/abs/path",
        r"paradox\core\v0",
        ".",
        "..",
        "paradox/core/./v0",
    ]

    for bad in bad_mounts:
        r = _run(
            [
                py,
                str(publish_tool),
                "--bundle-dir",
                str(bundle_dir),
                "--site-dir",
                str(site_dir),
                "--mount",
                bad,
            ]
        )
        assert r.returncode != 0, (
            "Bad mount unexpectedly succeeded (must fail-closed)\n"
            f"mount={bad!r}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        )
