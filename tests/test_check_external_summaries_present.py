#!/usr/bin/env python3
"""
Smoke tests for scripts/check_external_summaries_present.py

We intentionally run the script as a subprocess (as CI does), and assert return codes.
This catches syntax/indentation regressions and semantics regressions.

No external deps; stdlib only.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run_checker(repo: Path, external_dir: Path, extra_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    script = repo / "scripts" / "check_external_summaries_present.py"
    if not script.exists():
        raise FileNotFoundError(f"Missing checker script at: {script}")

    cmd = [sys.executable, str(script), "--external_dir", str(external_dir)]
    if extra_args:
        cmd.extend(extra_args)

    return subprocess.run(
        cmd,
        cwd=str(repo),
        text=True,
        capture_output=True,
    )


def assert_rc(res: subprocess.CompletedProcess[str], expected: int) -> None:
    if res.returncode != expected:
        print("=== Unexpected return code ===", file=sys.stderr)
        print(f"expected={expected} got={res.returncode}", file=sys.stderr)
        print("=== STDOUT ===", file=sys.stderr)
        print(res.stdout, file=sys.stderr)
        print("=== STDERR ===", file=sys.stderr)
        print(res.stderr, file=sys.stderr)
        raise AssertionError("checker returned unexpected exit code")


def main() -> int:
    repo = Path(__file__).resolve().parents[1]

    # Case 1: empty directory -> FAIL (no *_summary.json/.jsonl evidence)
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        res = run_checker(repo, d)
        assert_rc(res, 1)

    # Case 2: unrelated JSON present -> still FAIL (must not accept random *.json)
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "metadata.json").write_text(json.dumps({"hello": "world"}) + "\n", encoding="utf-8")
        res = run_checker(repo, d)
        assert_rc(res, 1)

    # Case 3: valid *_summary.json -> PASS
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "llamaguard_summary.json").write_text(json.dumps({"rate": 0.1}) + "\n", encoding="utf-8")
        res = run_checker(repo, d)
        assert_rc(res, 0)
       
    # Case 3b: adapter-style key (fail_rate) -> PASS (under --require_metric_key)
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "promptfoo_summary.json").write_text(json.dumps({"fail_rate": 0.02}) + "\n", encoding="utf-8")
        res = run_checker(repo, d, ["--require_metric_key"])
        assert_rc(res, 0)

    # Case 4: JSONL summary -> PASS
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "foo_summary.jsonl").write_text('{"rate": 0.0}\n', encoding="utf-8")
        res = run_checker(repo, d)
        assert_rc(res, 0)

    # Case 5: unparseable summary -> FAIL
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "bad_summary.json").write_text('{"rate":', encoding="utf-8")
        res = run_checker(repo, d)
        assert_rc(res, 1)

    # Case 6: --required missing file -> FAIL
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        res = run_checker(repo, d, ["--required", "missing_summary.json"])
        assert_rc(res, 1)

    # Case 7: --require_metric_key enforces metric keys (FAIL then PASS)
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # Has *_summary.json but no metric key -> FAIL under require_metric_key
        (d / "empty_summary.json").write_text(json.dumps({"note": "no metric here"}) + "\n", encoding="utf-8")
        res = run_checker(repo, d, ["--require_metric_key"])
        assert_rc(res, 1)

        # Add a metric key -> PASS
        (d / "empty_summary.json").write_text(json.dumps({"value": 0.0}) + "\n", encoding="utf-8")
        res = run_checker(repo, d, ["--require_metric_key"])
        assert_rc(res, 0)

    print("OK: check_external_summaries_present smoke tests passed")
    return 0

def test_smoke() -> None:
    # Pytest entrypoint: run the same smoke scenarios as the script.
    assert main() == 0

if __name__ == "__main__":
    raise SystemExit(main())
