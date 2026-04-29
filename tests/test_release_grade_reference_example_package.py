from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CHECKER = ROOT / "PULSE_safe_pack_v0" / "tools" / "check_release_grade_reference_run_v0.py"
EXAMPLE_DIR = ROOT / "examples" / "release_grade_reference_run_v0"

README = EXAMPLE_DIR / "README.md"
STATUS = EXAMPLE_DIR / "status.release_grade.pass.example.json"
MANIFEST = EXAMPLE_DIR / "release_authority_v0.release_grade.pass.example.json"


def test_release_grade_reference_example_files_exist() -> None:
    assert README.is_file()
    assert STATUS.is_file()
    assert MANIFEST.is_file()


def test_release_grade_reference_example_readme_references_existing_files() -> None:
    text = README.read_text(encoding="utf-8")

    assert "status.release_grade.pass.example.json" in text
    assert "release_authority_v0.release_grade.pass.example.json" in text

    assert str(STATUS.relative_to(ROOT)) in text
    assert str(MANIFEST.relative_to(ROOT)) in text


def test_release_grade_reference_example_checker_passes() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--status",
            str(STATUS),
            "--manifest",
            str(MANIFEST),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "OK: release-grade reference run criteria satisfied" in result.stdout


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
