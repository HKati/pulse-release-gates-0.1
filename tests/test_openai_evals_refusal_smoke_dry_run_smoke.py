#!/usr/bin/env python3
"""
OpenAI evals refusal smoke (dry-run) — wiring smoke only.

Design goals:
- Must run in CI PR/push context where secrets are not available.
- Must NOT require OPENAI_API_KEY (dry-run mode).
- Proves the wiring: dataset -> runner -> out json + status update path works.

This test intentionally runs the pipeline via subprocess (as CI would).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / "openai_evals_v0" / "run_refusal_smoke_to_pulse.py"
DATASET = ROOT / "openai_evals_v0" / "refusal_smoke.jsonl"


def _write_min_status(path: pathlib.Path) -> None:
    # Minimal status v1-like object; the eval runner may append gates/metrics.
    status = {
        "version": "1.0.0-test",
        "created_utc": "2026-02-18T00:00:00Z",
        "metrics": {"run_mode": "core"},
        "gates": {},
    }
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()

    # Hermeticize: CI PR/push has no secrets; match that.
    for k in [
        "OPENAI_API_KEY",
        "OPENAI_ORG_ID",
        "OPENAI_ORGANIZATION",
        "OPENAI_PROJECT",
        "OPENAI_BASE_URL",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
    ]:
        env.pop(k, None)

    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def _assert_rc(p: subprocess.CompletedProcess[str], expected: int) -> None:
    if p.returncode != expected:
        raise AssertionError(
            f"Unexpected return code: expected={expected} got={p.returncode}\n"
            f"CMD: {' '.join(p.args) if isinstance(p.args, list) else p.args}\n"
            f"STDOUT:\n{p.stdout}\n"
            f"STDERR:\n{p.stderr}\n"
        )


def test_openai_evals_refusal_smoke_dry_run() -> None:
    assert RUNNER.is_file(), f"Missing runner: {RUNNER}"
    assert DATASET.is_file(), f"Missing dataset: {DATASET}"

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        out_json = td / "refusal_smoke_result.json"
        status_json = td / "status.json"

        _write_min_status(status_json)

        # Force dry-run explicitly (no API calls, no API key required).
        p = _run(
            [
                sys.executable,
                str(RUNNER),
                "--dry-run",
                "--dataset",
                str(DATASET),
                "--out",
                str(out_json),
                "--status-json",
                str(status_json),
            ]
        )
        _assert_rc(p, 0)

        assert out_json.exists(), "Expected refusal smoke output json was not created"
        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert isinstance(data, (dict, list)), "Output must be valid JSON (dict or list)"
        # keep this intentionally loose: smoke validates wiring, not content schema

        # Ensure status remains JSON and keeps gates/metrics structure
        st = json.loads(status_json.read_text(encoding="utf-8"))
        assert isinstance(st, dict)
        assert "gates" in st and isinstance(st["gates"], dict)
        assert "metrics" in st and isinstance(st["metrics"], dict)


def main() -> int:
    try:
        test_openai_evals_refusal_smoke_dry_run()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: openai evals refusal smoke dry-run wiring passed")
    return 0


def test_smoke() -> None:
    # optional pytest entrypoint
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
