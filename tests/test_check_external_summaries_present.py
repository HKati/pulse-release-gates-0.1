#!/usr/bin/env python3
"""
Smoke tests for scripts/check_external_summaries_present.py.

The checker is intentionally exercised as a subprocess, matching CI behavior.

Security invariant:
- default strict/release discovery is canonical-only;
- decoy or non-canonical *_summary.json/jsonl files must fail by default;
- explicit --required may override discovery for an explicitly named operator check.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run_checker(
    repo: Path,
    external_dir: Path,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
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

    # Case 1: empty directory -> FAIL
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        res = run_checker(repo, d)
        assert_rc(res, 1)

    # Case 2: unrelated JSON present -> FAIL
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "metadata.json").write_text(
            json.dumps({"hello": "world"}) + "\n",
            encoding="utf-8",
        )
        res = run_checker(repo, d)
        assert_rc(res, 1)

    # Case 3: decoy JSON summary -> FAIL by default
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "foo_summary.json").write_text(
            json.dumps({"value": 0.0}) + "\n",
            encoding="utf-8",
        )
        res = run_checker(repo, d)
        assert_rc(res, 1)

    # Case 4: decoy JSONL summary -> FAIL by default
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "foo_summary.jsonl").write_text(
            '{"rate": 0.0}\n',
            encoding="utf-8",
        )
        res = run_checker(repo, d)
        assert_rc(res, 1)

    # Case 5: canonical JSON summary -> PASS
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "llamaguard_summary.json").write_text(
            json.dumps({"rate": 0.1}) + "\n",
            encoding="utf-8",
        )
        res = run_checker(repo, d)
        assert_rc(res, 0)

    # Case 6: canonical JSONL summary -> PASS
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "llamaguard_summary.jsonl").write_text(
            '{"rate": 0.0}\n',
            encoding="utf-8",
        )
        res = run_checker(repo, d)
        assert_rc(res, 0)

    # Case 7: canonical adapter-style key -> PASS under --require_metric_key
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "promptfoo_summary.json").write_text(
            json.dumps({"fail_rate": 0.02}) + "\n",
            encoding="utf-8",
        )
        res = run_checker(repo, d, ["--require_metric_key"])
        assert_rc(res, 0)

    # Case 8: canonical summary without metric key -> FAIL under --require_metric_key
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "promptfoo_summary.json").write_text(
            json.dumps({"note": "no metric here"}) + "\n",
            encoding="utf-8",
        )
        res = run_checker(repo, d, ["--require_metric_key"])
        assert_rc(res, 1)

    # Case 9: malformed canonical summary -> FAIL
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "llamaguard_summary.json").write_text(
            '{"rate":',
            encoding="utf-8",
        )
        res = run_checker(repo, d)
        assert_rc(res, 1)

    # Case 10: --required missing file -> FAIL
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        res = run_checker(repo, d, ["--required", "missing_summary.json"])
        assert_rc(res, 1)

    # Case 11: non-canonical metric summary -> FAIL by default,
    # but PASS when explicitly named by --required.
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "empty_summary.json").write_text(
            json.dumps({"value": 0.0}) + "\n",
            encoding="utf-8",
        )

        res = run_checker(repo, d, ["--require_metric_key"])
        assert_rc(res, 1)

        res = run_checker(
            repo,
            d,
            ["--required", "empty_summary.json", "--require_metric_key"],
        )
        assert_rc(res, 0)

    print("OK: check_external_summaries_present smoke tests passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
