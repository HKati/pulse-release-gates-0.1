#!/usr/bin/env python3
"""
Smoke test: openai_evals_v0 refusal smoke runner in --dry-run mode.

What this locks in:
- No network calls, no OPENAI_API_KEY required.
- refusal_smoke_result.json is contract-valid.
- Optional status.json patching works and is deterministic.
- Status patching is additive (does not wipe existing fields).
- --fail-on-false exits non-zero when gate_pass is false, but still writes artifacts.

Notes:
- Runnable directly (python ...), and exposes pytest entrypoints so CI running `pytest` executes it.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> None:
    subprocess.check_call(cmd)


def _run_rc(cmd: list[str]) -> int:
    p = subprocess.run(cmd, check=False)
    return p.returncode


def _write_seed_status(path: Path) -> None:
    """Write a status.json with pre-existing content that must be preserved by patching."""
    seed = {
        "metrics": {"preexisting_metric": 123},
        "gates": {"preexisting_gate": True},
        "keep_top_level": {"nested": "value"},
    }
    path.write_text(json.dumps(seed, indent=2) + "\n", encoding="utf-8")


def _sha256_and_lines(path: Path) -> tuple[int, str]:
    h = hashlib.sha256()
    n = 0
    with path.open("rb") as f:
        for bline in f:
            n += 1
            h.update(bline)
    return n, h.hexdigest()


def _assert_seed_preserved(status: dict) -> None:
    assert status.get("keep_top_level") == {"nested": "value"}, "top-level seed key was not preserved"

    metrics = status.get("metrics")
    assert isinstance(metrics, dict), f"status.metrics must be dict, got {type(metrics).__name__}"
    assert metrics.get("preexisting_metric") == 123, "preexisting metric was not preserved"

    gates = status.get("gates")
    assert isinstance(gates, dict), f"status.gates must be dict, got {type(gates).__name__}"
    assert gates.get("preexisting_gate") is True, "preexisting gate was not preserved"


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


def _assert_trace_has_provenance(status: dict, expected_lines: int, expected_sha: str) -> None:
    ev = (status.get("openai_evals_v0") or {}).get("refusal_smoke") or {}
    assert ev.get("dataset_lines") == expected_lines, (
        f"trace dataset_lines mismatch: {ev.get('dataset_lines')} != {expected_lines}"
    )
    assert ev.get("dataset_sha256") == expected_sha, "trace dataset_sha256 mismatch"


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

        # Seed status.json to ensure patching is additive.
        _write_seed_status(status)

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
            ]
        )

        assert out.exists(), "runner did not write refusal_smoke_result.json"
        assert status.exists(), "runner did not patch/create status.json"

        # Contract must pass
        _run([sys.executable, str(contract), "--in", str(out)])

        # Basic sanity of output
        r = _read_json(out)
        assert r.get("dry_run") is True, "expected dry_run=true"
        assert (r.get("result_counts") or {}).get("total", 0) > 0, "expected non-empty dataset => total > 0"
        assert r.get("gate_pass") is True, "expected non-empty dataset in dry-run => gate_pass True"
        expected_lines, expected_sha = _sha256_and_lines(dataset)
        assert r.get("dataset_lines") == expected_lines
        assert r.get("dataset_sha256") == expected_sha

        # Status patch must contain gate + metrics and must preserve seed fields
        s = _read_json(status)
        _assert_seed_preserved(s)
        _assert_has_metrics(s)
        _assert_has_gate(s, expect=True)
        _assert_trace_has_provenance(s, expected_lines, expected_sha)

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

        # Seed status.json to ensure patching is additive even on fail-closed runs.
        _write_seed_status(status)

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
            ]
        )

        assert out.exists(), "runner did not write refusal_smoke_result.json (empty dataset)"
        assert status.exists(), "runner did not patch/create status.json (empty dataset)"

        # Contract must still pass (fail-closed semantics)
        _run([sys.executable, str(contract), "--in", str(out)])

        r = _read_json(out)
        assert (r.get("result_counts") or {}).get("total", 123456789) == 0, "expected empty dataset => total == 0"
        assert r.get("gate_pass") is False, "expected empty dataset => gate_pass False (fail-closed)"
        expected_lines, expected_sha = _sha256_and_lines(empty)
        assert r.get("dataset_lines") == expected_lines
        assert r.get("dataset_sha256") == expected_sha

        s = _read_json(status)
        _assert_seed_preserved(s)
        _assert_has_metrics(s)
        _assert_has_gate(s, expect=False)
        _assert_trace_has_provenance(s, expected_lines, expected_sha)


def _test_fail_on_false_exits_nonzero_but_writes_outputs(root: Path) -> None:
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

        _write_seed_status(status)

        rc = _run_rc(
            [
                sys.executable,
                str(runner),
                "--dry-run",
                "--fail-on-false",
                "--dataset",
                str(empty),
                "--out",
                str(out),
                "--status-json",
                str(status),
            ]
        )

        # The runner currently uses exit code 1 when --fail-on-false is set and gate_pass is false.
        assert rc == 1, f"expected returncode=1 for --fail-on-false when gate fails, got {rc}"


        # Even on failure, artifacts must exist for debugging
        assert out.exists(), "runner must write refusal_smoke_result.json even when --fail-on-false triggers"
        assert status.exists(), "runner must patch/write status.json even when --fail-on-false triggers"

        # Contract must still pass (output is still a valid artifact)
        _run([sys.executable, str(contract), "--in", str(out)])

        r = _read_json(out)
        assert (r.get("result_counts") or {}).get("total", 123456789) == 0, "expected empty dataset => total == 0"
        assert r.get("gate_pass") is False, "expected gate_pass false in fail-closed case"
        expected_lines, expected_sha = _sha256_and_lines(empty)
        assert r.get("dataset_lines") == expected_lines
        assert r.get("dataset_sha256") == expected_sha

        s = _read_json(status)
        _assert_seed_preserved(s)
        _assert_has_gate(s, expect=False)
        _assert_trace_has_provenance(s, expected_lines, expected_sha)


# -----------------------
# Pytest entrypoints
# -----------------------

def test_non_empty_dataset_dry_run_additive_patch() -> None:
    _test_non_empty_dataset(_repo_root())


def test_empty_dataset_dry_run_fails_closed_additive_patch() -> None:
    _test_empty_dataset_fails_closed(_repo_root())


def test_fail_on_false_writes_artifacts_and_exits_2() -> None:
    _test_fail_on_false_exits_nonzero_but_writes_outputs(_repo_root())


# -----------------------
# Optional direct runner
# -----------------------

def main() -> int:
    root = _repo_root()
    _test_non_empty_dataset(root)
    _test_empty_dataset_fails_closed(root)
    _test_fail_on_false_exits_nonzero_but_writes_outputs(root)
    print("OK: openai_evals_v0 refusal smoke dry-run wiring is stable + contract-valid + additive status patch + fail-on-false semantics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
