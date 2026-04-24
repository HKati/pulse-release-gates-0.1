#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "build_space_relation_map_summary.py"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "topology" / "space_relation_map_v0_summary.md"
RELATIVE_TEST_OUTPUT = Path("tests/out/space_relation_map_build_smoke_summary.md")


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _backup_text(path: Path) -> tuple[bool, str | None]:
    if path.exists():
        return True, path.read_text(encoding="utf-8")
    return False, None


def _restore_text(path: Path, existed: bool, content: str | None) -> None:
    if existed:
        assert content is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    else:
        if path.exists():
            path.unlink()


def test_tool_compiles() -> None:
    cp = subprocess.run(
        [sys.executable, "-m", "py_compile", str(TOOL)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    combined = cp.stdout + cp.stderr
    assert cp.returncode == 0, combined


def test_build_with_default_output() -> None:
    existed, previous = _backup_text(DEFAULT_OUTPUT)
    try:
        cp = _run(REPO_ROOT)
        combined = cp.stdout + cp.stderr

        assert cp.returncode == 0, combined
        assert DEFAULT_OUTPUT.exists(), combined

        rendered = DEFAULT_OUTPUT.read_text(encoding="utf-8")
        assert "# PULSE Space Relation Map v0" in rendered, rendered
        assert "## Spaces and placements" in rendered, rendered
        assert "## Relations" in rendered, rendered
        assert "## Invariants" in rendered, rendered
        assert f"OK: built space relation map summary: {DEFAULT_OUTPUT}" in cp.stdout, combined
    finally:
        _restore_text(DEFAULT_OUTPUT, existed, previous)


def test_relative_out_is_normalized_against_repo_root() -> None:
    repo_target = REPO_ROOT / RELATIVE_TEST_OUTPUT
    existed, previous = _backup_text(repo_target)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            cp = _run(tmpdir_path, "--out", str(RELATIVE_TEST_OUTPUT))
            combined = cp.stdout + cp.stderr

            assert cp.returncode == 0, combined
            assert repo_target.exists(), combined
            assert not (tmpdir_path / RELATIVE_TEST_OUTPUT).exists(), combined

            rendered = repo_target.read_text(encoding="utf-8")
            assert "# PULSE Space Relation Map v0" in rendered, rendered
            assert f"OK: built space relation map summary: {repo_target}" in cp.stdout, combined
    finally:
        _restore_text(repo_target, existed, previous)


def main() -> None:
    test_tool_compiles()
    test_build_with_default_output()
    test_relative_out_is_normalized_against_repo_root()
    print("OK: build_space_relation_map_summary tool smoke tests passed")


if __name__ == "__main__":
    main()
