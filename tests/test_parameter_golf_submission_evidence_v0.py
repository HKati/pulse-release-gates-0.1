from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "parameter_golf_submission_evidence_v0.schema.json"
EXAMPLE_PATH = ROOT / "examples" / "parameter_golf_submission_evidence_v0.example.json"
TOOL_PATH = ROOT / "tools" / "verify_parameter_golf_submission_v0.py"


def test_example_validates_against_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    example = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=example, schema=schema)


def test_verifier_accepts_example() -> None:
    proc = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--evidence", str(EXAMPLE_PATH)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "VALID" in proc.stdout


def test_verifier_strict_rejects_semantic_mismatch(tmp_path: Path) -> None:
    broken = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    broken["artifact"]["total_bytes_int8_zlib"] += 10

    broken_path = tmp_path / "broken.json"
    broken_path.write_text(json.dumps(broken), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--evidence", str(broken_path), "--strict"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "Warnings:" in proc.stdout


def test_verifier_rejects_schema_violation(tmp_path: Path) -> None:
    broken = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    del broken["evaluation"]["val_bpb"]

    broken_path = tmp_path / "invalid.json"
    broken_path.write_text(json.dumps(broken), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--evidence", str(broken_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "INVALID" in proc.stdout
