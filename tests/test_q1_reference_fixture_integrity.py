#!/usr/bin/env python3
"""
Integrity smoke test for the checked-in Q1 reference labels fixture.

This test is intentionally:
- artifact-first
- deterministic
- self-contained
- runnable as a standalone script
- compatible with pytest discovery

It locks down:
1. the checked-in fixture bytes match the SHA-256 recorded in the manifest
2. the fixture row count matches the manifest sampling count
3. the fixture contains only the canonical deterministic JSONL rows
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


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
                candidate / "examples" / "q1_reference_input_manifest.json"
            ).is_file() and (
                candidate / "examples" / "q1_reference_labels.pass_120.jsonl"
            ).is_file():
                return candidate

    raise RuntimeError(
        "Could not locate repo root containing the checked-in Q1 reference "
        "manifest and labels fixture"
    )


ROOT = _find_repo_root()
MANIFEST = ROOT / "examples" / "q1_reference_input_manifest.json"
LABELS = ROOT / "examples" / "q1_reference_labels.pass_120.jsonl"
EXPECTED_ROW = {"label": "SUPPORTED", "eligible": True}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_q1_reference_fixture_matches_manifest_digest_and_sampling_count() -> None:
    manifest = _load_json(MANIFEST)

    raw = LABELS.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()

    actual_sha256 = hashlib.sha256(raw).hexdigest()
    expected_sha256 = manifest["hashes"]["input_sha256"]

    assert actual_sha256 == expected_sha256
    assert len(lines) == manifest["sampling"]["n"] == 120

    for i, line in enumerate(lines, start=1):
        assert line.strip() != "", f"blank JSONL row at line {i}"
        assert json.loads(line) == EXPECTED_ROW, f"unexpected JSONL row at line {i}"


def main() -> int:
    try:
        test_q1_reference_fixture_matches_manifest_digest_and_sampling_count()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1

    print("OK: Q1 reference fixture integrity smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
