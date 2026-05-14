from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


COMMANDS = [
    [
        sys.executable,
        "-m",
        "py_compile",
        "tools/verify_pulse_ref_ra1_package.py",
        "tests/test_pulse_ref_ra1_package_verifier_tool_smoke.py",
    ],
    [
        sys.executable,
        "tests/test_pulse_ref_ra1_package_verifier_tool_smoke.py",
    ],
    [
        sys.executable,
        "tests/test_pulse_ref_package_verifier_report_schema_v0.py",
    ],
    [
        sys.executable,
        "tests/test_pulse_ref_ra1_minimal_package_fixture.py",
    ],
]


def _run_command(command: list[str]) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        rendered = " ".join(command)
        raise AssertionError(
            f"RA1 operating proof command failed: {rendered}\n"
            f"returncode: {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def main() -> int:
    try:
        for command in COMMANDS:
            _run_command(command)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF RA1 operating proof smoke passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
