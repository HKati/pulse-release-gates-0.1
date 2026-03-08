#!/usr/bin/env python3
"""
Regression smoke test for augment_status.py external summary requirement modes.

Locks down three behaviors:

1. Default/onboarding mode remains permissive when no external summaries exist.
2. Strict mode fails closed when external summaries are explicitly required
   and none are present.
3. Strict mode preserves normal threshold evaluation when a valid summary exists.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "PULSE_safe_pack_v0" / "tools" / "augment_status.py"


def _write_status(path: pathlib.Path) -> None:
    status = {
        "version": "1.0.0-test",
        "created_utc": "2026-03-08T00:00:00Z",
        "metrics": {"run_mode": "core"},
        "gates": {},
    }
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_refusal_summary(path: pathlib.Path) -> None:
    obj = {
        "n": 10,
        "delta": 0.0,
        "ci_low": 0.0,
        "ci_high": 0.0,
        "policy": "balanced",
        "delta_min": 0.10,
        "delta_strict": 0.10,
        "p_mcnemar": 1.0,
        "pass_min": True,
        "pass_strict": True,
        "pass": True,
    }
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_thresholds(path: pathlib.Path, promptfoo_fail_rate_max: float = 0.10) -> None:
    path.write_text(
        (
            "external_overall_policy: all\n"
            f"promptfoo_fail_rate_max: {promptfoo_fail_rate_max}\n"
        ),
        encoding="utf-8",
    )


def _write_promptfoo_summary(path: pathlib.Path, fail_rate: float) -> None:
    obj = {"fail_rate": fail_rate}
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(
    status_path: pathlib.Path,
    thresholds_path: pathlib.Path,
    external_dir: pathlib.Path,
    require_external_summaries: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    cmd = [
        sys.executable,
        str(TOOL),
        "--status",
        str(status_path),
        "--thresholds",
        str(thresholds_path),
        "--external_dir",
        str(external_dir),
    ]
    if require_external_summaries:
        cmd.append("--require_external_summaries")
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def _load_status(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_rc(p: subprocess.CompletedProcess[str], rc: int) -> None:
    if p.returncode != rc:
        raise AssertionError(
            f"Unexpected return code: expected={rc} got={p.returncode}\n"
            f"STDOUT:\n{p.stdout}\n"
            f"STDERR:\n{p.stderr}\n"
        )


def _assert_bool(actual: object, expected: bool, label: str, status: dict) -> None:
    if actual is not expected:
        raise AssertionError(
            f"{label}: expected={expected!r} got={actual!r}\n"
            f"STATUS:\n{json.dumps(status, indent=2, ensure_ascii=False)}\n"
        )


def test_default_mode_keeps_onboarding_pass_without_external_summaries() -> None:
    assert TOOL.is_file(), f"Missing tool at: {TOOL}"

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        artifacts_dir = td / "artifacts"
        external_dir = td / "external"
        artifacts_dir.mkdir()
        external_dir.mkdir()

        status_path = artifacts_dir / "status.json"
        refusal_summary_path = artifacts_dir / "refusal_delta_summary.json"
        thresholds_path = td / "external_thresholds.yaml"

        _write_status(status_path)
        _write_refusal_summary(refusal_summary_path)
        _write_thresholds(thresholds_path)

        p = _run(
            status_path,
            thresholds_path,
            external_dir,
            require_external_summaries=False,
        )
        _assert_rc(p, 0)

        status = _load_status(status_path)

        _assert_bool(status["refusal_delta_pass"], True, "refusal_delta_pass", status)
        _assert_bool(status["external_summaries_present"], False, "external_summaries_present", status)
        _assert_bool(status["gates"]["external_summaries_present"], False, "gates.external_summaries_present", status)
        _assert_bool(status["external_all_pass"], True, "external_all_pass", status)
        _assert_bool(status["gates"]["external_all_pass"], True, "gates.external_all_pass", status)
        _assert_bool(status["external"]["all_pass"], True, "external.all_pass", status)

        if status["external"]["summary_count"] != 0:
            raise AssertionError(f"Expected summary_count=0, got {status['external']['summary_count']!r}")


def test_strict_mode_fails_closed_without_external_summaries() -> None:
    assert TOOL.is_file(), f"Missing tool at: {TOOL}"

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        artifacts_dir = td / "artifacts"
        external_dir = td / "external"
        artifacts_dir.mkdir()
        external_dir.mkdir()

        status_path = artifacts_dir / "status.json"
        refusal_summary_path = artifacts_dir / "refusal_delta_summary.json"
        thresholds_path = td / "external_thresholds.yaml"

        _write_status(status_path)
        _write_refusal_summary(refusal_summary_path)
        _write_thresholds(thresholds_path)

        p = _run(
            status_path,
            thresholds_path,
            external_dir,
            require_external_summaries=True,
        )
        _assert_rc(p, 0)

        status = _load_status(status_path)

        _assert_bool(status["refusal_delta_pass"], True, "refusal_delta_pass", status)
        _assert_bool(status["external_summaries_present"], False, "external_summaries_present", status)
        _assert_bool(status["gates"]["external_summaries_present"], False, "gates.external_summaries_present", status)
        _assert_bool(status["external_all_pass"], False, "external_all_pass", status)
        _assert_bool(status["gates"]["external_all_pass"], False, "gates.external_all_pass", status)
        _assert_bool(status["external"]["all_pass"], False, "external.all_pass", status)

        if status["external"]["summary_count"] != 0:
            raise AssertionError(f"Expected summary_count=0, got {status['external']['summary_count']!r}")


def test_strict_mode_preserves_threshold_eval_when_summary_exists() -> None:
    assert TOOL.is_file(), f"Missing tool at: {TOOL}"

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        artifacts_dir = td / "artifacts"
        external_dir = td / "external"
        artifacts_dir.mkdir()
        external_dir.mkdir()

        status_path = artifacts_dir / "status.json"
        refusal_summary_path = artifacts_dir / "refusal_delta_summary.json"
        thresholds_path = td / "external_thresholds.yaml"
        promptfoo_summary_path = external_dir / "promptfoo_summary.json"

        _write_status(status_path)
        _write_refusal_summary(refusal_summary_path)
        _write_thresholds(thresholds_path, promptfoo_fail_rate_max=0.10)
        _write_promptfoo_summary(promptfoo_summary_path, fail_rate=0.05)

        p = _run(
            status_path,
            thresholds_path,
            external_dir,
            require_external_summaries=True,
        )
        _assert_rc(p, 0)

        status = _load_status(status_path)

        _assert_bool(status["refusal_delta_pass"], True, "refusal_delta_pass", status)
        _assert_bool(status["external_summaries_present"], True, "external_summaries_present", status)
        _assert_bool(status["gates"]["external_summaries_present"], True, "gates.external_summaries_present", status)
        _assert_bool(status["external_all_pass"], True, "external_all_pass", status)
        _assert_bool(status["gates"]["external_all_pass"], True, "gates.external_all_pass", status)
        _assert_bool(status["external"]["all_pass"], True, "external.all_pass", status)

        if status["external"]["summary_count"] != 1:
            raise AssertionError(f"Expected summary_count=1, got {status['external']['summary_count']!r}")

        metrics = status["external"]["metrics"]
        if len(metrics) != 1:
            raise AssertionError(f"Expected 1 external metric, got {len(metrics)}\nSTATUS:\n{json.dumps(status, indent=2, ensure_ascii=False)}")

        metric = metrics[0]
        if metric["name"] != "promptfoo_fail_rate":
            raise AssertionError(f"Unexpected metric name: {metric['name']!r}")
        if metric["value"] != 0.05:
            raise AssertionError(f"Unexpected metric value: {metric['value']!r}")
        if metric["threshold"] != 0.10:
            raise AssertionError(f"Unexpected metric threshold: {metric['threshold']!r}")
        _assert_bool(metric["pass"], True, "external.metrics[0].pass", status)


def main() -> int:
    try:
        test_default_mode_keeps_onboarding_pass_without_external_summaries()
        test_strict_mode_fails_closed_without_external_summaries()
        test_strict_mode_preserves_threshold_eval_when_summary_exists()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1

    print("OK: augment_status strict summary requirement smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
