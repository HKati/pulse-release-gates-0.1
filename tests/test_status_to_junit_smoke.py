#!/usr/bin/env python3
"""
Smoke test for PULSE_safe_pack_v0/tools/status_to_junit.py.

Runs the exporter on a tiny hermetic status fixture and asserts the produced
JUnit XML has the expected tests/failures counts and gate testcase names.

This file is intentionally runnable both:
- as a "pytest-style" test module (test_* function), and
- as a standalone script (main()) because CI runs `python <file>` directly.
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

def _parse_iso_utc(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _run(status_path: pathlib.Path, out_path: pathlib.Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()

    # Keep the test hermetic: do not rely on environment-driven defaults.
    env.pop("PULSE_STATUS", None)
    env.pop("PULSE_JUNIT", None)

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
        env=env,
    )


def _get_testsuite_root(xml_path: pathlib.Path) -> ET.Element:
    """
    Accept either:
      - <testsuite ...> as root, or
      - <testsuites><testsuite .../></testsuites> wrapper.
    """
    root = ET.parse(xml_path).getroot()

    if root.tag == "testsuite":
        return root

    if root.tag == "testsuites":
        ts = root.find("testsuite")
        if ts is None:
            raise AssertionError("Expected <testsuite> inside <testsuites>, but none found")
        return ts

    raise AssertionError(f"Unexpected JUnit XML root element: <{root.tag}>")


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

        # Deterministic fixture writing (nice for debugging / stable diffs)
        status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        r = _run(status_path, out_path)
        if r.returncode != 0:
            raise AssertionError(
                f"Exporter failed: exit={r.returncode}\n"
                f"STDOUT:\n{r.stdout}\n"
                f"STDERR:\n{r.stderr}"
            )

        assert out_path.is_file(), "Expected JUnit XML output file to be created"

        testsuite = _get_testsuite_root(out_path)
        ts_attr = (testsuite.attrib.get("timestamp") or "").strip()
        assert ts_attr, "Expected testsuite timestamp attribute to be present"
        assert _parse_iso_utc(ts_attr) == _parse_iso_utc(status["created_utc"])

        tests = int(testsuite.attrib.get("tests", "0"))
        failures = int(testsuite.attrib.get("failures", "0"))
        assert tests == 3, f"Expected tests=3, got {tests}"
        assert failures == 1, f"Expected failures=1, got {failures}"

        testcase_names = [tc.attrib.get("name", "") for tc in testsuite.findall("testcase")]
        assert set(testcase_names) == {"gate_a", "gate_b", "gate_c"}, f"Unexpected testcase names: {testcase_names}"

        for tc in testsuite.findall("testcase"):
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
