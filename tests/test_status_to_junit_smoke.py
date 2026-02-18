#!/usr/bin/env python3
"""
Smoke test for PULSE_safe_pack_v0/tools/status_to_junit.py.

Runs the exporter on a tiny hermetic status fixture and asserts the produced
JUnit XML has the expected tests/failures counts and gate testcase names.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPORTER = REPO_ROOT / "PULSE_safe_pack_v0" / "tools" / "status_to_junit.py"


def _run(status_path: pathlib.Path, out_path: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(EXPORTER),
            "--status",
            str(status_path),
            "--out",
            str(out_path),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )


def test_status_to_junit_smoke() -> None:
    assert EXPORTER.is_file(), f"Exporter not found at {EXPORTER}"

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        status_path = td / "status.json"
        out_path = td / "junit.xml"

        status = {
            "version": "1.0.0-core",
            "created_utc": "2026-02-17T00:00:00Z",
            "metrics": {"run_mode": "core"},
            "gates": {
                "gate_a": True,
                "gate_b": False,
                "gate_c": True,
            },
        }
        status_path.write_text(json.dumps(status), encoding="utf-8")

        r = _run(status_path, out_path)
        if r.returncode != 0:
            raise AssertionError(f"Exporter failed: exit={r.returncode}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}")

        assert out_path.is_file(), "Expected JUnit XML output file to be created"

        root = ET.parse(out_path).getroot()
        assert root.tag == "testsuite", f"Expected <testsuite> root, got <{root.tag}>"

        tests = int(root.attrib.get("tests", "0"))
        failures = int(root.attrib.get("failures", "0"))
        assert tests == 3, f"Expected tests=3, got {tests}"
        assert failures == 1, f"Expected failures=1, got {failures}"

        testcase_names = [tc.attrib.get("name", "") for tc in root.findall("testcase")]
        assert set(testcase_names) == {"gate_a", "gate_b", "gate_c"}, f"Unexpected testcase names: {testcase_names}"

        # Ensure failing gate has a <failure> element
        for tc in root.findall("testcase"):
            name = tc.attrib.get("name")
            has_failure = tc.find("failure") is not None
            if name == "gate_b":
                assert has_failure, "Expected gate_b to have a <failure>"
            else:
                assert not has_failure, f"Did not expect {name} to have a <failure>"


def main() -> int:
    try:
        test_status_to_junit_smoke()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1

    print("OK: status_to_junit smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
