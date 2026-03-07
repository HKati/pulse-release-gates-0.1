#!/usr/bin/env python3
"""
Regression smoke test for strict external summary metric-key recognition.

Locks down that the strict precheck accepts the canonical Azure metric key
used by augment_status.py / external thresholds, while still failing when
no recognized metric key is present.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "check_external_summaries_present.py"


def _write_json(path: pathlib.Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(
    external_dir: pathlib.Path,
    required: list[str] | None = None,
    require_metric_key: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    cmd = [sys.executable, str(TOOL), "--external_dir", str(external_dir)]
    for name in required or []:
        cmd.extend(["--required", name])
    if require_metric_key:
        cmd.append("--require_metric_key")
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def _assert_rc(p: subprocess.CompletedProcess[str], rc: int) -> None:
    if p.returncode != rc:
        raise AssertionError(
            f"Unexpected return code: expected={rc} got={p.returncode}\n"
            f"STDOUT:\n{p.stdout}\n"
            f"STDERR:\n{p.stderr}\n"
        )


def test_strict_checker_accepts_canonical_azure_metric_key() -> None:
    assert TOOL.is_file(), f"Missing tool at: {TOOL}"

    with tempfile.TemporaryDirectory() as td:
        ext = pathlib.Path(td)
        _write_json(
            ext / "azure_eval_summary.json",
            {"azure_indirect_jailbreak_rate": 0.01},
        )
        p = _run(
            ext,
            required=["azure_eval_summary.json"],
            require_metric_key=True,
        )
        _assert_rc(p, 0)


def test_strict_checker_still_fails_without_any_recognized_metric_key() -> None:
    assert TOOL.is_file(), f"Missing tool at: {TOOL}"

    with tempfile.TemporaryDirectory() as td:
        ext = pathlib.Path(td)
        _write_json(
            ext / "azure_eval_summary.json",
            {"tool": "azure-eval", "generated_at": "2026-03-07T00:00:00Z"},
        )
        p = _run(
            ext,
            required=["azure_eval_summary.json"],
            require_metric_key=True,
        )
        _assert_rc(p, 1)


def main() -> int:
    try:
        test_strict_checker_accepts_canonical_azure_metric_key()
        test_strict_checker_still_fails_without_any_recognized_metric_key()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1

    print("OK: strict external summary Azure-key regression smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
