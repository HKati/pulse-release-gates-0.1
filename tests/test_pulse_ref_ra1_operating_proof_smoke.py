from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "tests" / "out" / "pulse_ref_ra1_operating_proof_summary.json"


COMMANDS = [
    {
        "name": "verifier_py_compile",
        "argv": [
            sys.executable,
            "-m",
            "py_compile",
            "tools/verify_pulse_ref_ra1_package.py",
            "tests/test_pulse_ref_ra1_package_verifier_tool_smoke.py",
        ],
    },
    {
        "name": "ra1_package_verifier_smoke",
        "argv": [
            sys.executable,
            "tests/test_pulse_ref_ra1_package_verifier_tool_smoke.py",
        ],
    },
    {
        "name": "verifier_report_schema_smoke",
        "argv": [
            sys.executable,
            "tests/test_pulse_ref_package_verifier_report_schema_v0.py",
        ],
    },
    {
        "name": "ra1_minimal_package_fixture_smoke",
        "argv": [
            sys.executable,
            "tests/test_pulse_ref_ra1_minimal_package_fixture.py",
        ],
    },
]


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _run_command(command: dict[str, Any]) -> dict[str, Any]:
    argv = command["argv"]

    result = subprocess.run(
        argv,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    return {
        "name": command["name"],
        "command": argv,
        "returncode": result.returncode,
        "ok": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _write_summary(summary: dict[str, Any]) -> None:
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    command_results: list[dict[str, Any]] = []
    errors: list[str] = []

    for command in COMMANDS:
        result = _run_command(command)
        command_results.append(result)

        if not result["ok"]:
            rendered = " ".join(result["command"])
            errors.append(
                f"RA1 operating proof command failed: {rendered} "
                f"(returncode={result['returncode']})"
            )
            break

    summary: dict[str, Any] = {
        "schema": "pulse_ref_ra1_operating_proof_summary_v0",
        "ok": errors == [],
        "created_utc": _utc_now(),
        "commands": command_results,
        "errors": errors,
        "authority_boundary": {
            "proof_summary_role": "test_aggregation_record",
            "creates_release_authority": False,
        },
    }

    _write_summary(summary)

    if errors:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 1

    print("OK: PULSE-REF RA1 operating proof smoke passed")
    print(f"OK: wrote RA1 operating proof summary: {SUMMARY_PATH}")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
