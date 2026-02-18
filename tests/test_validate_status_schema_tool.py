#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import sys
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "validate_status_schema.py"
SCHEMA = REPO_ROOT / "schemas" / "status" / "status_v1.schema.json"


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


def main() -> int:
    if not TOOL.is_file():
        raise SystemExit(f"validate_status_schema.py not found at: {TOOL}")
    if not SCHEMA.is_file():
        raise SystemExit(f"status_v1 schema not found at: {SCHEMA}")

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)

        # Minimal valid instance for status_v1:
        # - required: version, created_utc, metrics, gates
        valid = {
            "version": "1.0.0-core",
            "created_utc": "2026-02-17T00:00:00Z",
            "metrics": {"run_mode": "core"},
            "gates": {"q1_grounded_ok": True},
        }
        valid_path = td / "valid_status.json"
        valid_path.write_text(json.dumps(valid), encoding="utf-8")

        r_ok = _run(SCHEMA, valid_path)
        if r_ok.returncode != 0:
            print("STDOUT:\n", r_ok.stdout)
            print("STDERR:\n", r_ok.stderr)
            raise SystemExit(f"Expected valid status to pass, got exit={r_ok.returncode}")

        # Invalid: missing required keys (e.g., gates)
        invalid = {
            "version": "1.0.0-core",
            "created_utc": "2026-02-17T00:00:00Z",
            "metrics": {"run_mode": "core"},
        }
        invalid_path = td / "invalid_status.json"
        invalid_path.write_text(json.dumps(invalid), encoding="utf-8")

        r_bad = _run(SCHEMA, invalid_path)
        if r_bad.returncode == 0:
            print("STDOUT:\n", r_bad.stdout)
            print("STDERR:\n", r_bad.stderr)
            raise SystemExit("Expected invalid status to fail validation, but it passed")

        # Assert it emits CI-friendly ::error:: lines
        out = (r_bad.stdout or "") + "\n" + (r_bad.stderr or "")
        if "::error::" not in out:
            print("OUTPUT:\n", out)
            raise SystemExit("Expected ::error:: annotation in output for invalid status")

    print("OK: validate_status_schema tool smoke tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
