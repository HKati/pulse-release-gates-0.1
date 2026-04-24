#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "render_space_relation_map_summary.py"
EXAMPLE = REPO_ROOT / "examples" / "space_relation_map_v0.manual.json"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_render_to_stdout() -> None:
    cp = _run(str(EXAMPLE))
    combined = cp.stdout + cp.stderr

    assert cp.returncode == 0, combined
    assert "# PULSE Space Relation Map v0" in cp.stdout, combined
    assert "## Spaces and placements" in cp.stdout, combined
    assert "## Relations" in cp.stdout, combined
    assert "## Invariants" in cp.stdout, combined
    assert "### `core`" in cp.stdout, combined
    assert "`status_json` (artifact)" in cp.stdout, combined
    assert "`quality_ledger` cannot override `space:core`" in cp.stdout, combined
    assert (
        "`external_summary` may become normatively relevant for `space:core` "
        "only if policy/workflow promotes it"
    ) in cp.stdout, combined


def test_render_to_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "space_relation_map_summary.md"
        cp = _run(str(EXAMPLE), "--out", str(out))
        combined = cp.stdout + cp.stderr

        assert cp.returncode == 0, combined
        assert out.exists(), combined

        rendered = out.read_text(encoding="utf-8")
        assert "# PULSE Space Relation Map v0" in rendered, rendered
        assert "## Non-override relations" in rendered, rendered
        assert "## Policy-dependent promotion relations" in rendered, rendered
        assert "## Invariants" in rendered, rendered
        assert f"OK: wrote space relation map summary: {out}" in cp.stdout, combined


def main() -> None:
    test_render_to_stdout()
    test_render_to_file()
    print("OK: render_space_relation_map_summary tool smoke tests passed")


if __name__ == "__main__":
    main()
