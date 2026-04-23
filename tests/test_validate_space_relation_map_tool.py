#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "validate_space_relation_map.py"
EXAMPLE = REPO_ROOT / "examples" / "space_relation_map_v0.manual.json"
SCHEMA = REPO_ROOT / "schemas" / "schemas" / "space_relation_map_v0.schema.json"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _load_example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_validate_with_default_schema_path() -> None:
    cp = _run(str(EXAMPLE))
    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert (
        "OK: space_relation_map_v0 artifact is schema-valid and reference-consistent"
        in cp.stdout
    )


def test_validate_with_explicit_schema_path() -> None:
    cp = _run(str(EXAMPLE), "--schema", str(SCHEMA))
    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert (
        "OK: space_relation_map_v0 artifact is schema-valid and reference-consistent"
        in cp.stdout
    )


def test_unknown_space_reference_fails() -> None:
    doc = _load_example()
    doc["placements"][0]["space_id"] = "missing_space"

    with tempfile.TemporaryDirectory() as tmpdir:
        broken = Path(tmpdir) / "broken_space_relation_map.json"
        broken.write_text(json.dumps(doc, indent=2), encoding="utf-8")

        cp = _run(str(broken), "--schema", str(SCHEMA))
        combined = cp.stdout + cp.stderr

        assert cp.returncode != 0, combined
        assert (
            "ERROR: placement references unknown space_id: missing_space"
            in combined
        ), combined


def main() -> None:
    test_validate_with_default_schema_path()
    test_validate_with_explicit_schema_path()
    test_unknown_space_reference_fails()
    print("OK: validate_space_relation_map tool smoke tests passed")


if __name__ == "__main__":
    main()
