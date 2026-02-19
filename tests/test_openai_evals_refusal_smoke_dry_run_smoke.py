#!/usr/bin/env python3
"""
OpenAI evals refusal smoke (dry-run) — wiring + status patch smoke.

Goals:
- Must run in CI PR/push context with NO secrets.
- Must force --dry-run (no network, no OPENAI_API_KEY).
- Must verify that --status-json is actually patched (not just preserved).
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


def _count_nonempty_jsonl_lines(path: pathlib.Path) -> int:
    text = path.read_text(encoding="utf-8")
    return sum(1 for line in text.splitlines() if line.strip())


def _write_min_status(path: pathlib.Path) -> None:
    # Minimal v1-like scaffold; runner should patch metrics + gates.
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

    expected_total = _count_nonempty_jsonl_lines(DATASET)
    assert expected_total > 0, "refusal_smoke.jsonl must be non-empty for meaningful smoke coverage"

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        out_json = td / "refusal_smoke_result.json"
        status_json = td / "status.json"

        _write_min_status(status_json)
        before = status_json.read_text(encoding="utf-8")

        gate_key = "openai_evals_refusal_smoke_pass_test"
        model = "gpt-4.1"

        # Force dry-run explicitly (no API calls, no API key required).
        p = _run(
            [
                sys.executable,
                str(RUNNER),
                "--dry-run",
                "--dataset",
                str(DATASET),
                "--model",
                model,
                "--gate-key",
                gate_key,
                "--out",
                str(out_json),
                "--status-json",
                str(status_json),
            ]
        )
        _assert_rc(p, 0)

        # Output JSON: validate key wiring (not full schema lock)
        assert out_json.exists(), "Expected refusal smoke output json was not created"
        result = json.loads(out_json.read_text(encoding="utf-8"))
        assert isinstance(result, dict)
        assert result.get("dry_run") is True
        assert result.get("gate_key") == gate_key
        assert isinstance(result.get("result_counts"), dict)

        counts = result["result_counts"]
        assert int(counts.get("total", -1)) == expected_total
        assert int(counts.get("passed", -1)) == expected_total
        assert int(counts.get("failed", -1)) == 0
        assert int(counts.get("errored", -1)) == 0
        assert result.get("gate_pass") is True

        # Status JSON must be patched (not just preserved)
        after = status_json.read_text(encoding="utf-8")
        assert after != before, "Expected runner to patch status.json, but file content did not change"

        st = json.loads(after)
        assert isinstance(st, dict)
        assert "gates" in st and isinstance(st["gates"], dict)
        assert "metrics" in st and isinstance(st["metrics"], dict)

        # Gate patch (both canonical + mirrored key)
        assert st["gates"].get(gate_key) is True
        assert st.get(gate_key) is True

        # Metrics patch
        m = st["metrics"]
        assert int(m.get("openai_evals_refusal_smoke_total", -1)) == expected_total
        assert int(m.get("openai_evals_refusal_smoke_passed", -1)) == expected_total
        assert int(m.get("openai_evals_refusal_smoke_failed", -1)) == 0
        assert int(m.get("openai_evals_refusal_smoke_errored", -1)) == 0
        fail_rate = float(m.get("openai_evals_refusal_smoke_fail_rate", 999.0))
        assert abs(fail_rate - 0.0) < 1e-12

        # Trace patch
        ov0 = st.get("openai_evals_v0")
        assert isinstance(ov0, dict) and "refusal_smoke" in ov0
        trace = ov0["refusal_smoke"]
        assert isinstance(trace, dict)
        assert trace.get("dry_run") is True
        assert trace.get("dataset") == str(DATASET)
        assert trace.get("model") == model
        assert trace.get("result_json") == str(out_json)


def main() -> int:
    try:
        test_openai_evals_refusal_smoke_dry_run()
    except AssertionError as e:
        print(f"ERROR: {e}")
        return 1
    print("OK: openai evals refusal smoke dry-run wiring+status patch passed")
    return 0


def test_smoke() -> None:
    # optional pytest entrypoint
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
