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
RENDERER_PATH = ROOT / "tools" / "render_parameter_golf_review_receipt_v0.py"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def make_minimal_evidence(total_bytes: int, kind: str | None = None) -> dict:
    artifact = {
        "code_bytes": 1,
        "model_bytes_int8_zlib": total_bytes - 1,
        "total_bytes_int8_zlib": total_bytes,
    }
    if kind is not None:
        artifact["kind"] = kind

    return {
        "schema_version": "0.1",
        "submission_type": "non_record",
        "artifact": artifact,
        "evaluation": {
            "mode": "standard",
            "val_bpb": 1.23,
        },
    }


def write_direct_limit_schema(path: Path, default_limit: int) -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "submission_type", "artifact", "evaluation"],
        "properties": {
            "schema_version": {"const": "0.1"},
            "submission_type": {"type": "string"},
            "artifact": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "code_bytes",
                    "model_bytes_int8_zlib",
                    "total_bytes_int8_zlib",
                ],
                "properties": {
                    "code_bytes": {"type": "integer", "minimum": 0},
                    "model_bytes_int8_zlib": {"type": "integer", "minimum": 0},
                    "total_bytes_int8_zlib": {"type": "integer", "minimum": 0},
                    "artifact_limit_bytes": {
                        "type": "integer",
                        "minimum": 1,
                        "default": default_limit,
                    },
                },
            },
            "evaluation": {
                "type": "object",
                "additionalProperties": False,
                "required": ["mode", "val_bpb"],
                "properties": {
                    "mode": {"type": "string", "enum": ["standard"]},
                    "val_bpb": {"type": "number"},
                },
            },
        },
    }
    write_json(path, schema)


def write_branching_anchor_schema(path: Path) -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "submission_type", "artifact", "evaluation"],
        "properties": {
            "schema_version": {"const": "0.1"},
            "submission_type": {"type": "string"},
            "artifact": {"$ref": "#artifact"},
            "evaluation": {
                "type": "object",
                "additionalProperties": False,
                "required": ["mode", "val_bpb"],
                "properties": {
                    "mode": {"type": "string", "enum": ["standard"]},
                    "val_bpb": {"type": "number"},
                },
            },
        },
        "$defs": {
            "artifact_union": {
                "$anchor": "artifact",
                "oneOf": [
                    {"$ref": "#/$defs/small_artifact"},
                    {"$ref": "#/$defs/large_artifact"},
                ],
            },
            "small_artifact": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "kind",
                    "code_bytes",
                    "model_bytes_int8_zlib",
                    "total_bytes_int8_zlib",
                ],
                "properties": {
                    "kind": {"const": "small"},
                    "code_bytes": {"type": "integer", "minimum": 0},
                    "model_bytes_int8_zlib": {"type": "integer", "minimum": 0},
                    "total_bytes_int8_zlib": {"type": "integer", "minimum": 0},
                    "artifact_limit_bytes": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 10,
                    },
                },
            },
            "large_artifact": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "kind",
                    "code_bytes",
                    "model_bytes_int8_zlib",
                    "total_bytes_int8_zlib",
                ],
                "properties": {
                    "kind": {"const": "large"},
                    "code_bytes": {"type": "integer", "minimum": 0},
                    "model_bytes_int8_zlib": {"type": "integer", "minimum": 0},
                    "total_bytes_int8_zlib": {"type": "integer", "minimum": 0},
                    "artifact_limit_bytes": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 100,
                    },
                },
            },
        },
    }
    write_json(path, schema)


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
    write_json(broken_path, broken)

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
    write_json(broken_path, broken)

    proc = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--evidence", str(broken_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "INVALID" in proc.stdout


def test_verifier_reports_missing_jsonschema_cleanly() -> None:
    proc = subprocess.run(
        [sys.executable, "-I", "-S", str(TOOL_PATH), "--evidence", str(EXAMPLE_PATH)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "Missing dependency: 'jsonschema'" in (proc.stderr + proc.stdout)


def test_verifier_rejects_invalid_custom_schema_json(tmp_path: Path) -> None:
    bad_schema_path = tmp_path / "bad-schema.json"
    bad_schema_path.write_text(json.dumps({"type": 123}), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--evidence",
            str(EXAMPLE_PATH),
            "--schema",
            str(bad_schema_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["valid_schema"] is False
    assert payload["error_kind"] == "schema_error"


def test_verifier_rejects_scalar_custom_schema_json(tmp_path: Path) -> None:
    scalar_schema_path = tmp_path / "scalar-schema.json"
    scalar_schema_path.write_text("0", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--evidence",
            str(EXAMPLE_PATH),
            "--schema",
            str(scalar_schema_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["valid_schema"] is False
    assert payload["error_kind"] == "schema_error"


def test_verifier_strict_accepts_counted_tokenizer_bytes(tmp_path: Path) -> None:
    evidence = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    evidence["artifact"]["tokenizer_counted"] = True
    evidence["artifact"]["tokenizer_bytes_if_counted"] = 321
    evidence["artifact"]["total_bytes_int8_zlib"] = (
        evidence["artifact"]["code_bytes"]
        + evidence["artifact"]["model_bytes_int8_zlib"]
        + evidence["artifact"]["tokenizer_bytes_if_counted"]
    )
    evidence_path = tmp_path / "counted-tokenizer.json"
    write_json(evidence_path, evidence)

    proc = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--evidence", str(evidence_path), "--strict"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "Warnings:" not in proc.stdout


def test_verifier_warns_when_counted_tokenizer_bytes_missing(tmp_path: Path) -> None:
    evidence = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    evidence["artifact"]["tokenizer_counted"] = True
    evidence["artifact"].pop("tokenizer_bytes_if_counted", None)
    evidence_path = tmp_path / "missing-counted-tokenizer.json"
    write_json(evidence_path, evidence)

    proc = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--evidence", str(evidence_path), "--strict"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert (
        "tokenizer_counted is true but tokenizer_bytes_if_counted is missing/non-integer"
        in proc.stdout
    )


def test_verifier_json_mode_reports_missing_evidence_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing-evidence.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--evidence",
            str(missing_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["valid_schema"] is False
    assert payload["error_kind"] == "evidence_file_not_found"


def test_verifier_json_mode_reports_invalid_evidence_json(tmp_path: Path) -> None:
    bad_evidence_path = tmp_path / "bad-evidence.json"
    bad_evidence_path.write_text("{not valid json", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--evidence",
            str(bad_evidence_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["valid_schema"] is False
    assert payload["error_kind"] == "evidence_json_decode_error"


def test_verifier_json_mode_reports_missing_schema_file(tmp_path: Path) -> None:
    missing_schema_path = tmp_path / "missing-schema.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--evidence",
            str(EXAMPLE_PATH),
            "--schema",
            str(missing_schema_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["valid_schema"] is False
    assert payload["error_kind"] == "schema_file_not_found"


def test_verifier_json_mode_reports_invalid_schema_json(tmp_path: Path) -> None:
    bad_schema_path = tmp_path / "bad-schema.json"
    bad_schema_path.write_text("{not valid json", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--evidence",
            str(EXAMPLE_PATH),
            "--schema",
            str(bad_schema_path),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["valid_schema"] is False
    assert payload["error_kind"] == "schema_json_decode_error"


def test_verifier_strict_uses_schema_default_limit_when_field_is_omitted(
    tmp_path: Path,
) -> None:
    schema_path = tmp_path / "direct-default-schema.json"
    write_direct_limit_schema(schema_path, default_limit=10)

    evidence = make_minimal_evidence(total_bytes=11)
    evidence_path = tmp_path / "omitted-limit-evidence.json"
    write_json(evidence_path, evidence)

    proc = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--evidence",
            str(evidence_path),
            "--schema",
            str(schema_path),
            "--json",
            "--strict",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["valid_schema"] is True
    assert payload["summary"]["artifact_limit_bytes"] == 10
    assert payload["summary"]["artifact_limit_bytes_declared"] is None
    assert (
        "artifact total (11) exceeds effective schema-default limit (10)"
        in payload["warnings"]
    )


def test_verifier_uses_matching_oneof_branch_default_limit_with_local_anchor(
    tmp_path: Path,
) -> None:
    schema_path = tmp_path / "branching-anchor-schema.json"
    write_branching_anchor_schema(schema_path)

    evidence = make_minimal_evidence(total_bytes=50, kind="large")
    evidence_path = tmp_path / "large-branch-evidence.json"
    write_json(evidence_path, evidence)

    proc = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--evidence",
            str(evidence_path),
            "--schema",
            str(schema_path),
            "--json",
            "--strict",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["valid_schema"] is True
    assert payload["warning_count"] == 0
    assert payload["summary"]["artifact_limit_bytes"] == 100
    assert payload["summary"]["artifact_limit_bytes_declared"] is None


def test_renderer_uses_matching_oneof_branch_default_limit_with_local_anchor(
    tmp_path: Path,
) -> None:
    schema_path = tmp_path / "branching-anchor-schema.json"
    write_branching_anchor_schema(schema_path)

    evidence = make_minimal_evidence(total_bytes=50, kind="large")
    evidence_path = tmp_path / "large-branch-evidence.json"
    write_json(evidence_path, evidence)

    proc = subprocess.run(
        [
            sys.executable,
            str(RENDERER_PATH),
            "--evidence",
            str(evidence_path),
            "--schema",
            str(schema_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)

    assert payload["validation"]["valid_schema"] is True
    assert payload["validation"]["warning_count"] == 0
    assert payload["review_surface"]["artifact_limit_bytes"] is None
    assert payload["review_surface"]["artifact_limit_bytes_effective"] == 100
    assert payload["review_surface"]["artifact_limit_source"] == "schema_default"
    assert payload["review_surface"]["artifact_within_limit"] is True
