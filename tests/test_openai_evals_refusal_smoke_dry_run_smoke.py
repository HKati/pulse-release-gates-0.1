#!/usr/bin/env python3
"""
Smoke test: openai_evals_v0 refusal smoke runner in --dry-run mode.

What this locks in:
- No network calls, no OPENAI_API_KEY required.
- refusal_smoke_result.json is contract-valid.
- Optional status.json patching works and is deterministic.

Run (standalone):
  python tests/test_openai_evals_refusal_smoke_dry_run_smoke.py

Also pytest-friendly: collected via test_* entrypoints below.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _run(cmd: list[str], *, cwd: Path) -> None:
    subprocess.check_call(cmd, cwd=str(cwd))


def _assert_has_metrics(status: dict) -> None:
    m = status.get("metrics") or {}
    required = [
        "openai_evals_refusal_smoke_total",
        "openai_evals_refusal_smoke_passed",
        "openai_evals_refusal_smoke_failed",
        "openai_evals_refusal_smoke_errored",
        "openai_evals_refusal_smoke_fail_rate",
    ]
    for k in required:
        assert k in m, f"missing metric: {k} (metrics keys={sorted(m.keys())})"


def _assert_has_gate(status: dict, expect: bool) -> None:
    gates = status.get("gates") or {}
    assert "openai_evals_refusal_smoke_pass" in gates, (
        f"missing gate in status.gates (keys={sorted(gates.keys())})"
    )
    assert gates["openai_evals_refusal_smoke_pass"] is expect, (
        f"gate mismatch: {gates['openai_evals_refusal_smoke_pass']} != {expect}"
    )
    # mirrored at top-level
    assert status.get("openai_evals_refusal_smoke_pass") is expect, "top-level mirror missing/mismatch"


def _test_non_empty_dataset(root: Path) -> None:
    runner = root / "openai_evals_v0" / "run_refusal_smoke_to_pulse.py"
    contract = root / "scripts" / "check_openai_evals_refusal_smoke_result_v0_contract.py"
    dataset = root / "openai_evals_v0" / "refusal_smoke.jsonl"

    assert runner.exists(), f"missing: {runner}"
    assert contract.exists(), f"missing: {contract}"
    assert dataset.exists(), f"missing: {dataset}"

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        out = base / "refusal_smoke_result.json"
        status = base / "status.json"

        _run(
            [
                sys.executable,
                str(runner),
                "--dry-run",
                "--dataset",
                str(dataset),
                "--out",
                str(out),
                "--status-json",
                str(status),
            ],
            cwd=root,
        )

        assert out.exists(), "runner did not write refusal_smoke_result.json"
        assert status.exists(), "runner did not patch/create status.json"

        # Contract must pass
        _run([sys.executable, str(contract), "--in", str(out)], cwd=root)

        # Basic sanity of output
        r = _read_json(out)
        assert r.get("dry_run") is True, "expected dry_run=true"
        assert isinstance(r.get("status"), str) and r["status"].strip(), "expected non-empty status string"
        assert r["status"].strip() in ("completed", "succeeded"), "expected terminal success status for passing run"
        rc = r.get("result_counts") or {}
        assert rc.get("total", 0) > 0, "expected non-empty dataset => total > 0"
        assert r.get("gate_pass") is True, "expected non-empty dataset in dry-run => gate_pass True"
        # fail_rate should be consistent with failed/total (contract enforces this; keep a quick assert too)
        assert abs(float(r.get("fail_rate", -1.0)) - (float(rc.get("failed", 0)) / float(rc.get("total", 1)))) < 1e-6

        # Status patch must contain gate + metrics
        s = _read_json(status)
        _assert_has_metrics(s)
        _assert_has_gate(s, expect=True)

        # Trace block should exist (non-breaking if shape expands later)
        ev = (s.get("openai_evals_v0") or {}).get("refusal_smoke") or {}
        assert ev.get("dry_run") is True, "expected openai_evals_v0.refusal_smoke.dry_run=true"


def _test_empty_dataset_fails_closed(root: Path) -> None:
    runner = root / "openai_evals_v0" / "run_refusal_smoke_to_pulse.py"
    contract = root / "scripts" / "check_openai_evals_refusal_smoke_result_v0_contract.py"

    assert runner.exists(), f"missing: {runner}"
    assert contract.exists(), f"missing: {contract}"

    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        empty = base / "empty.jsonl"
        empty.write_text("", encoding="utf-8")

        out = base / "refusal_smoke_result.json"
        status = base / "status.json"

        _run(
            [
                sys.executable,
                str(runner),
                "--dry-run",
                "--dataset",
                str(empty),
                "--out",
                str(out),
                "--status-json",
                str(status),
            ],
            cwd=root,
        )

        assert out.exists(), "runner did not write refusal_smoke_result.json (empty dataset)"
        assert status.exists(), "runner did not patch/create status.json (empty dataset)"

        # Contract must still pass (fail-closed semantics)
        _run([sys.executable, str(contract), "--in", str(out)], cwd=root)

        r = _read_json(out)
        rc = r.get("result_counts") or {}
        assert rc.get("total", 123456789) == 0, "expected empty dataset => total == 0"
        assert r.get("gate_pass") is False, "expected empty dataset => gate_pass False (fail-closed)"
        # In our fail-closed semantics, fail_rate should be 1.0 when total==0
        assert abs(float(r.get("fail_rate", -1.0)) - 1.0) < 1e-9, "expected fail_rate==1.0 when total==0"

        s = _read_json(status)
        _assert_has_metrics(s)
        _assert_has_gate(s, expect=False)


# -------------------------
# Pytest entrypoints
# -------------------------
def test_openai_evals_refusal_smoke_dry_run_non_empty_dataset() -> None:
    _test_non_empty_dataset(_repo_root())


def test_openai_evals_refusal_smoke_dry_run_empty_dataset_fails_closed() -> None:
    _test_empty_dataset_fails_closed(_repo_root())


def main() -> int:
    root = _repo_root()
    _test_non_empty_dataset(root)
    _test_empty_dataset_fails_closed(root)
    print("OK: openai_evals_v0 refusal smoke dry-run wiring is stable + contract-valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
