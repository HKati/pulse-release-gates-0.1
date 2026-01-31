#!/usr/bin/env python3
"""
Smoke tests for PULSE_safe_pack_v0/tools/augment_status.py.

Goals:
- Catch syntax/indent regressions (script must run).
- Validate external summary folding across common formats:
  - JSON and JSONL
  - adapter-style keys (violation_rate, fail_rate, new_critical, attack_detect_rate)
- Specifically validate Azure behavior:
  - prefer azure_indirect_jailbreak_rate over generic rate/value when both exist
  - fallback to rate when the named scalar is missing
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_augment(status_path: Path, thresholds_path: Path, external_dir: Path) -> None:
    root = _repo_root()
    script = root / "PULSE_safe_pack_v0" / "tools" / "augment_status.py"
    print(f"[smoke] augment_status.py={script} sha256={__import__('hashlib').sha256(script.read_bytes()).hexdigest()}", flush=True)

  assert script.exists(), f"augment_status.py not found at {script}"

    subprocess.check_call(
        [
            sys.executable,
            str(script),
            "--status",
            str(status_path),
            "--thresholds",
            str(thresholds_path),
            "--external_dir",
            str(external_dir),
        ]
    )


def _load_status(status_path: Path) -> dict:
    return json.loads(status_path.read_text(encoding="utf-8"))


def _find_metric(out: dict, name: str) -> dict:
    metrics = (out.get("external") or {}).get("metrics") or []
    for m in metrics:
        if m.get("name") == name:
            return m
    raise AssertionError(f"metric not found: {name}; metrics={metrics}")


def test_external_all_pass_true_with_valid_summaries(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)

    status = tmp_path / "status.json"
    thresholds = tmp_path / "external_thresholds.yaml"
    ext = tmp_path / "external"
    ext.mkdir(parents=True, exist_ok=True)

    _write_json(status, {"gates": {}, "metrics": {}})

    # Lenient thresholds so everything passes.
    _write_text(
        thresholds,
        "\n".join(
            [
                "external_overall_policy: all",
                "llamaguard_violation_rate_max: 0.20",
                "promptguard_attack_detect_rate_max: 0.20",
                "garak_new_critical_max: 1.0",
                "azure_indirect_jailbreak_rate_max: 0.20",
                "promptfoo_fail_rate_max: 0.20",
                "deepeval_fail_rate_max: 0.20",
                "",
            ]
        ),
    )

    # JSON with canonical-ish keys
    _write_json(ext / "llamaguard_summary.json", {"violation_rate": 0.10})
    _write_json(ext / "promptguard_summary.json", {"attack_detect_rate": 0.05})
    _write_json(ext / "garak_summary.json", {"new_critical": 0})

    # Azure: provide both named scalar and rate (should still pass under lenient threshold)
    _write_json(
        ext / "azure_eval_summary.json",
        {"azure_indirect_jailbreak_rate": 0.01, "rate": 0.19, "failure_rates": {"x": 0.01}},
    )

    # JSONL (common in pipelines)
    _write_text(ext / "promptfoo_summary.jsonl", '{"fail_rate": 0.02}\n')
    _write_text(ext / "deepeval_summary.jsonl", '{"fail_rate": 0.03}\n')

    _run_augment(status, thresholds, ext)

    out = _load_status(status)
    assert out["gates"]["external_all_pass"] is True
    assert out["external"]["all_pass"] is True
    assert out["external"]["summary_count"] >= 1
    assert out["external"]["summaries_present"] is True
    assert out["gates"]["external_summaries_present"] is True


def test_azure_prefers_named_scalar_over_rate(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)

    status = tmp_path / "status.json"
    thresholds = tmp_path / "external_thresholds.yaml"
    ext = tmp_path / "external"
    ext.mkdir(parents=True, exist_ok=True)

    _write_json(status, {"gates": {}, "metrics": {}})

    # Strict enough to demonstrate preference:
    # - named scalar is 0.07 (should FAIL)
    # - rate is 0.01 (would PASS if incorrectly used)
    _write_text(
        thresholds,
        "\n".join(
            [
                "external_overall_policy: all",
                "azure_indirect_jailbreak_rate_max: 0.05",
                "",
            ]
        ),
    )

    _write_json(
        ext / "azure_eval_summary.json",
        {
            "azure_indirect_jailbreak_rate": 0.07,
            "rate": 0.01,
            "value": 0.01,
            "failure_rates": {"indirect": 0.07},
        },
    )

    _run_augment(status, thresholds, ext)

    out = _load_status(status)
    assert out["gates"]["external_all_pass"] is False
    m = _find_metric(out, "azure_indirect_jailbreak_rate")
    assert abs(float(m["value"]) - 0.07) < 1e-9
    assert m["pass"] is False


def test_azure_fallback_to_rate_when_named_missing(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)

    status = tmp_path / "status.json"
    thresholds = tmp_path / "external_thresholds.yaml"
    ext = tmp_path / "external"
    ext.mkdir(parents=True, exist_ok=True)

    _write_json(status, {"gates": {}, "metrics": {}})

    _write_text(
        thresholds,
        "\n".join(
            [
                "external_overall_policy: all",
                "azure_indirect_jailbreak_rate_max: 0.05",
                "",
            ]
        ),
    )

    # No named scalar -> should fall back to rate (=0.03) and PASS
    _write_json(ext / "azure_eval_summary.json", {"rate": 0.03, "failure_rates": {"x": 0.03}})

    _run_augment(status, thresholds, ext)

    out = _load_status(status)
    assert out["gates"]["external_all_pass"] is True
    m = _find_metric(out, "azure_indirect_jailbreak_rate")
    assert abs(float(m["value"]) - 0.03) < 1e-9
    assert m["pass"] is True


def test_parse_error_marks_metric_and_fails(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)

    status = tmp_path / "status.json"
    thresholds = tmp_path / "external_thresholds.yaml"
    ext = tmp_path / "external"
    ext.mkdir(parents=True, exist_ok=True)

    _write_json(status, {"gates": {}, "metrics": {}})

    _write_text(
        thresholds,
        "\n".join(
            [
                "external_overall_policy: all",
                "llamaguard_violation_rate_max: 0.20",
                "",
            ]
        ),
    )

    # Invalid JSON -> parse_error True, pass False, external_all_pass False
    _write_text(ext / "llamaguard_summary.json", "{not json")

    _run_augment(status, thresholds, ext)

    out = _load_status(status)
    assert out["gates"]["external_all_pass"] is False

    m = _find_metric(out, "llamaguard_violation_rate")
    assert m.get("parse_error") is True
    assert m["pass"] is False


def main() -> int:
    # Standalone runner (CI calls this file directly via subprocess).
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)

        test_external_all_pass_true_with_valid_summaries(base / "t1")
        test_azure_prefers_named_scalar_over_rate(base / "t2")
        test_azure_fallback_to_rate_when_named_missing(base / "t3")
        test_parse_error_marks_metric_and_fails(base / "t4")

    print("augment_status smoke tests: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
