#!/usr/bin/env python3
"""
Smoke test for the checked-in Q1 reference input manifest example.

This test is intentionally:
- artifact-first
- self-contained
- runnable as a standalone script
- compatible with pytest discovery
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema


def _find_repo_root() -> Path:
    starts = []
    try:
        starts.append(Path(__file__).resolve().parent)
    except NameError:
        pass
    starts.append(Path.cwd().resolve())

    seen = set()
    for start in starts:
        for candidate in (start, *start.parents):
            if candidate in seen:
                continue
            seen.add(candidate)
            if (
                candidate / "schemas" / "dataset_manifest.schema.json"
            ).is_file() and (
                candidate / "examples" / "q1_reference_input_manifest.json"
            ).is_file():
                return candidate

    raise RuntimeError(
        "Could not locate repo root containing the dataset manifest schema "
        "and Q1 reference input manifest example"
    )


ROOT = _find_repo_root()
SCHEMA = ROOT / "schemas" / "dataset_manifest.schema.json"
EXAMPLE = ROOT / "examples" / "q1_reference_input_manifest.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_q1_reference_input_manifest_example_matches_shared_schema() -> None:
    schema = _load_json(SCHEMA)
    manifest = _load_json(EXAMPLE)

    jsonschema.validate(instance=manifest, schema=schema)

    assert manifest["dataset_id"] == "q1-reference-pass-120-v0"
    assert manifest["source"]["kind"] == "artifact"
    assert manifest["source"]["uri"] == "examples/q1_reference_labels.pass_120.jsonl"
    assert manifest["sampling"]["strategy"] == "full"
    assert manifest["sampling"]["n"] == 120
    assert manifest["extensions"]["lane"] == "q1_reference"
    assert manifest["extensions"]["track"] == "shadow"


def main() -> int:
    try:
        test_q1_reference_input_manifest_example_matches_shared_schema()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1

    print("OK: Q1 reference input manifest example smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
