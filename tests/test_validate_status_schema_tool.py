#!/usr/bin/env python3
"""
Hermetic smoke tests for tools/validate_status_schema.py.

Goals:
- Runnable as a plain script: python tests/test_validate_status_schema_tool.py
- Discoverable by pytest: contains test_* functions
- Robust when jsonschema is missing:
  * if jsonschema is installed: validate OK path + FAIL path
  * if jsonschema is missing: tool emits CI-friendly ::error:: and exits 2
- Regression guard: repo status_v1 schema enforces boolean-only gate values.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "validate_status_schema.py"
STATUS_V1_SCHEMA = REPO_ROOT / "schemas" / "status" / "status_v1.schema.json"


def _have_jsonschema() -> bool:
    try:
        import jsonschema  # noqa: F401
        return True
    except Exception:
        return False


def _run(schema_path: pathlib.Path, status_path: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--schema",
            str(schema_path),
            "--status",
            str(status_path),
            "--max-errors",
            "5",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )


def _out(r: subprocess.CompletedProcess[str]) -> str:
    return (r.stdout or "") + "\n" + (r.stderr or "")


def test_repo_status_v1_schema_enforces_boolean_gates() -> None:
    """
    Regression guard: ensure the repo's own status_v1 schema rejects non-boolean gate values.
    """
    assert STATUS_V1_SCHEMA.is_file(), f"status_v1 schema not found at {STATUS_V1_SCHEMA}"

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)

        valid = {
            "version": "1.0.0-test",
            "created_utc": "2026-02-17T00:00:00Z",
            "metrics": {"run_mode": "core"},
            "gates": {"q1_grounded_ok": True},
        }
        valid_path = td / "valid_status_v1.json"
        valid_path.write_text(json.dumps(valid), encoding="utf-8")

        invalid = {
            "version": "1.0.0-test",
            "created_utc": "2026-02-17T00:00:00Z",
            "metrics": {"run_mode": "core"},
            "gates": {"q1_grounded_ok": "true"},  # WRONG TYPE: must be boolean
        }
        invalid_path = td / "invalid_status_v1.json"
        invalid_path.write_text(json.dumps(invalid), encoding="utf-8")

        r_ok = _run(STATUS_V1_SCHEMA, valid_path)
        out_ok = _out(r_ok)
        assert r_ok.returncode == 0, f"Expected valid v1 status to pass\n{out_ok}"

        r_bad = _run(STATUS_V1_SCHEMA, invalid_path)
        out_bad = _out(r_bad)
        assert r_bad.returncode != 0, "Expected invalid gate type to fail schema validation"
        assert "::error::" in out_bad, f"Expected CI-friendly ::error:: on schema failure\n{out_bad}"
        # Keep this assertion loose: message text can vary slightly across jsonschema versions.
        assert "boolean" in out_bad.lower(), f"Expected mention of boolean type in error output\n{out_bad}"


def test_validate_status_schema_tool_smoke() -> None:
    """
    Minimal hermetic tool test (independent of repo schemas).
    Also handles dependency-missing behavior deterministically.
    """
    assert TOOL.is_file(), f"validate_status_schema tool not found at {TOOL}"

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)

        # Minimal Draft 2020-12 schema for a "status-like" object.
        # Keep it tiny and hermetic: no repo artifacts required.
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["version", "created_utc", "metrics", "gates"],
            "properties": {
                "version": {"type": "string"},
                "created_utc": {"type": "string"},
                "metrics": {"type": "object"},
                "gates": {"type": "object"},
            },
            "additionalProperties": True,
        }
        schema_path = td / "schema.json"
        schema_path.write_text(json.dumps(schema), encoding="utf-8")

        valid = {
            "version": "1.0.0-core",
            "created_utc": "2026-02-17T00:00:00Z",
            "metrics": {"run_mode": "core"},
            "gates": {"q1_grounded_ok": True},
        }
        valid_path = td / "valid_status.json"
        valid_path.write_text(json.dumps(valid), encoding="utf-8")

        invalid = {
            "version": "1.0.0-core",
            "created_utc": "2026-02-17T00:00:00Z",
            "metrics": {"run_mode": "core"},
            # missing "gates"
        }
        invalid_path = td / "invalid_status.json"
        invalid_path.write_text(json.dumps(invalid), encoding="utf-8")

        have = _have_jsonschema()

        # Always run once to cover either:
        # - normal validation path (jsonschema present)
        # - dependency-missing path (jsonschema absent)
        r_ok = _run(schema_path, valid_path)
        out_ok = _out(r_ok)

        if not have:
            # Dependency-light environments: exit 2 + CI-friendly ::error::
            assert r_ok.returncode == 2, (
                f"Expected exit 2 when jsonschema is missing, got exit={r_ok.returncode}\n{out_ok}"
            )
            assert "::error::" in out_ok, f"Expected ::error:: annotation when dependency missing\n{out_ok}"
            assert "jsonschema" in out_ok.lower(), f"Expected mention of jsonschema in output\n{out_ok}"
            return

        # jsonschema is available => valid should pass
        assert r_ok.returncode == 0, f"Expected valid status to pass, got exit={r_ok.returncode}\n{out_ok}"

        # invalid should fail and emit ::error::
        r_bad = _run(schema_path, invalid_path)
        out_bad = _out(r_bad)
        assert r_bad.returncode != 0, "Expected invalid status to fail validation"
        assert "::error::" in out_bad, f"Expected ::error:: annotations on validation failure\n{out_bad}"

        # Extra regression guard (repo schema): enforce boolean-only gates
        test_repo_status_v1_schema_enforces_boolean_gates()


def main() -> int:
    try:
        test_validate_status_schema_tool_smoke()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: validate_status_schema tool smoke tests passed")
    return 0


def test_smoke() -> None:
    # optional pytest entrypoint
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
