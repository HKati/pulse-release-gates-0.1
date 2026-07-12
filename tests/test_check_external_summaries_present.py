#!/usr/bin/env python3
"""
Smoke tests for scripts/check_external_summaries_present.py.

The checker is intentionally exercised as a subprocess, matching CI behavior.

Security invariant:
- default strict/release discovery is canonical-only;
- decoy or non-canonical *_summary.json/jsonl files must fail by default;
- explicit --required may override discovery for an explicitly named operator check;
- metric presence accepts legacy flat summaries and canonical metrics[] carriers;
- empty or incomplete canonical metrics[] carriers fail closed.
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
    script = (
        repo
        / "scripts"
        / "check_external_summaries_present.py"
    )

    if not script.exists():
        raise FileNotFoundError(
            f"Missing checker script at: {script}"
        )

    cmd = [
        sys.executable,
        str(script),
        "--external_dir",
        str(external_dir),
    ]

    if extra_args:
        cmd.extend(extra_args)

    return subprocess.run(
        cmd,
        cwd=str(repo),
        text=True,
        capture_output=True,
    )


def assert_rc(
    res: subprocess.CompletedProcess[str],
    expected: int,
) -> None:
    if res.returncode != expected:
        print(
            "=== Unexpected return code ===",
            file=sys.stderr,
        )

        print(
            f"expected={expected} "
            f"got={res.returncode}",
            file=sys.stderr,
        )

        print(
            "=== STDOUT ===",
            file=sys.stderr,
        )

        print(
            res.stdout,
            file=sys.stderr,
        )

        print(
            "=== STDERR ===",
            file=sys.stderr,
        )

        print(
            res.stderr,
            file=sys.stderr,
        )

        raise AssertionError(
            "checker returned unexpected exit code"
        )


def write_json(
    path: Path,
    payload: object,
) -> None:
    path.write_text(
        json.dumps(
            payload,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    repo = Path(__file__).resolve().parents[1]

    # Case 1: empty directory -> FAIL
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        result = run_checker(
            repo,
            external_dir,
        )

        assert_rc(result, 1)

    # Case 2: unrelated JSON present -> FAIL
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        write_json(
            external_dir / "metadata.json",
            {
                "hello": "world",
            },
        )

        result = run_checker(
            repo,
            external_dir,
        )

        assert_rc(result, 1)

    # Case 3: decoy JSON summary -> FAIL by default
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        write_json(
            external_dir / "foo_summary.json",
            {
                "value": 0.0,
            },
        )

        result = run_checker(
            repo,
            external_dir,
        )

        assert_rc(result, 1)

    # Case 4: decoy JSONL summary -> FAIL by default
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        (
            external_dir
            / "foo_summary.jsonl"
        ).write_text(
            '{"rate": 0.0}\n',
            encoding="utf-8",
        )

        result = run_checker(
            repo,
            external_dir,
        )

        assert_rc(result, 1)

    # Case 5: canonical legacy-flat JSON summary -> PASS
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        write_json(
            external_dir
            / "llamaguard_summary.json",
            {
                "rate": 0.1,
            },
        )

        result = run_checker(
            repo,
            external_dir,
        )

        assert_rc(result, 0)

    # Case 6: canonical legacy-flat JSONL summary -> PASS
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        (
            external_dir
            / "llamaguard_summary.jsonl"
        ).write_text(
            '{"rate": 0.0}\n',
            encoding="utf-8",
        )

        result = run_checker(
            repo,
            external_dir,
        )

        assert_rc(result, 0)

    # Case 7: canonical adapter-style flat key
    # -> PASS with metric check
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        write_json(
            external_dir
            / "promptfoo_summary.json",
            {
                "fail_rate": 0.02,
            },
        )

        result = run_checker(
            repo,
            external_dir,
            [
                "--require_metric_key",
            ],
        )

        assert_rc(result, 0)

    # Case 8: flat canonical summary without metric
    # -> FAIL with metric check
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        write_json(
            external_dir
            / "promptfoo_summary.json",
            {
                "note": "no metric here",
            },
        )

        result = run_checker(
            repo,
            external_dir,
            [
                "--require_metric_key",
            ],
        )

        assert_rc(result, 1)

    # Case 9: malformed canonical summary -> FAIL
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        (
            external_dir
            / "llamaguard_summary.json"
        ).write_text(
            '{"rate":',
            encoding="utf-8",
        )

        result = run_checker(
            repo,
            external_dir,
        )

        assert_rc(result, 1)

    # Case 10: --required missing file -> FAIL
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        result = run_checker(
            repo,
            external_dir,
            [
                "--required",
                "missing_summary.json",
            ],
        )

        assert_rc(result, 1)

    # Case 11: a non-canonical metric summary fails
    # default discovery but may be explicitly named by
    # an operator through --required.
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        write_json(
            external_dir
            / "empty_summary.json",
            {
                "value": 0.0,
            },
        )

        result = run_checker(
            repo,
            external_dir,
            [
                "--require_metric_key",
            ],
        )

        assert_rc(result, 1)

        result = run_checker(
            repo,
            external_dir,
            [
                "--required",
                "empty_summary.json",
                "--require_metric_key",
            ],
        )

        assert_rc(result, 0)

    # Case 12: external_summary_v1-style metrics[]
    # carrier with key + value -> PASS.
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        write_json(
            external_dir
            / "llamaguard_summary.json",
            {
                "metrics": [
                    {
                        "key": (
                            "llamaguard_violation_rate"
                        ),
                        "value": 0.0,
                        "passed": True,
                    }
                ],
            },
        )

        result = run_checker(
            repo,
            external_dir,
            [
                "--require_metric_key",
            ],
        )

        assert_rc(result, 0)

    # Case 13: canonical metrics[] must not be empty.
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        write_json(
            external_dir
            / "llamaguard_summary.json",
            {
                "metrics": [],
            },
        )

        result = run_checker(
            repo,
            external_dir,
            [
                "--require_metric_key",
            ],
        )

        assert_rc(result, 1)

    # Case 14: canonical metric object without
    # value -> FAIL.
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        write_json(
            external_dir
            / "llamaguard_summary.json",
            {
                "metrics": [
                    {
                        "key": (
                            "llamaguard_violation_rate"
                        ),
                        "passed": True,
                    }
                ],
            },
        )

        result = run_checker(
            repo,
            external_dir,
            [
                "--require_metric_key",
            ],
        )

        assert_rc(result, 1)

    # Case 15: canonical metric object requires
    # a non-empty key.
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        write_json(
            external_dir
            / "llamaguard_summary.json",
            {
                "metrics": [
                    {
                        "key": "   ",
                        "value": 0.0,
                        "passed": True,
                    }
                ],
            },
        )

        result = run_checker(
            repo,
            external_dir,
            [
                "--require_metric_key",
            ],
        )

        assert_rc(result, 1)

    # Case 16: external_summary_v1-style JSONL
    # metrics[] carrier -> PASS.
    with tempfile.TemporaryDirectory() as td:
        external_dir = Path(td)

        (
            external_dir
            / "llamaguard_summary.jsonl"
        ).write_text(
            json.dumps(
                {
                    "metrics": [
                        {
                            "key": (
                                "llamaguard_violation_rate"
                            ),
                            "value": 0.0,
                            "passed": True,
                        }
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = run_checker(
            repo,
            external_dir,
            [
                "--require_metric_key",
            ],
        )

        assert_rc(result, 0)

    print(
        "OK: check_external_summaries_present "
        "smoke tests passed"
    )

    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
