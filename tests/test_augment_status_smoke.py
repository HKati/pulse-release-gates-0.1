#!/usr/bin/env python3
"""
Smoke tests for PULSE_safe_pack_v0/tools/augment_status.py.

Goal:
- Catch syntax/indent regressions early (script must run).
- Verify external summary key handling across common adapter formats:
  - JSON and JSONL
  - keys like violation_rate, fail_rate, new_critical
  - parse_error behavior for invalid JSON

This file is runnable both:
- under pytest (test_* functions), and
- as a standalone script (python tests/test_augment_status_smoke.py).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _run_augment(status_path: Path, thresholds_path: Path, external_dir: Path) -> None:
    root = _repo_root()
    script = root / "PULSE_safe_pack_v0" / "tools" / "augment_status.py"
    assert script.exists(), f"augment_status.py not found at {script}"

    print(
        f"[smoke] augment_status.py={script} sha256={__import__('hashlib').sha256(script.read_bytes()).hexdigest()}",
        flush=True,
    )

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



def test_external_all_pass_true_with_valid_summaries(tmp_path: Path) -> None:
    status = tmp_path / "status.json"
    thresholds = tmp_path / "external_thresholds.yaml"
    ext = tmp_path / "external"
    ext.mkdir(parents=True, exist_ok=True)

    _write_json(status, {"gates": {}, "metrics": {}})

    # Keep thresholds lenient so these pass.
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
    _write_json(ext / "azure_eval_summary.json", {"rate": 0.01})

    # JSONL (common in pipelines)
    _write_text(ext / "promptfoo_summary.jsonl", '{"fail_rate": 0.02}\n')
    _write_text(ext / "deepeval_summary.jsonl", '{"fail_rate": 0.03}\n')

    _run_augment(status, thresholds, ext)

    out = json.loads(status.read_text(encoding="utf-8"))
    assert out["gates"]["external_all_pass"] is True
    assert out["external"]["all_pass"] is True
    assert out["external"]["summary_count"] >= 1
    assert out["external"]["summaries_present"] is True


def test_external_all_pass_false_when_threshold_exceeded(tmp_path: Path) -> None:
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
                "promptfoo_fail_rate_max: 0.01",
                "",
            ]
        ),
    )

    # Exceeds threshold -> should fail.
    _write_json(ext / "promptfoo_summary.json", {"fail_rate": 0.10})

    _run_augment(status, thresholds, ext)

    out = json.loads(status.read_text(encoding="utf-8"))
    assert out["gates"]["external_all_pass"] is False
    assert out["external"]["all_pass"] is False
    assert any(m.get("name") == "promptfoo_fail_rate" for m in out["external"]["metrics"])


def test_parse_error_marks_metric_and_fails(tmp_path: Path) -> None:
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

    # Invalid JSON -> parse_error True, pass False, and external_all_pass False (policy=all and oks contains False)
    _write_text(ext / "llamaguard_summary.json", "{not json")

    _run_augment(status, thresholds, ext)

    out = json.loads(status.read_text(encoding="utf-8"))
    assert out["gates"]["external_all_pass"] is False

    metrics = out["external"]["metrics"]
    assert any((m.get("name") == "llamaguard_violation_rate" and m.get("parse_error") is True) for m in metrics)


def main() -> int:
    # Minimal self-runner so this can be executed without pytest.
    # We just run the file via pytest-like expectations by calling the tests directly.
    # (CI in this repo already runs some tests as standalone scripts.)
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)

        test_external_all_pass_true_with_valid_summaries(tmp / "t1")
        test_external_all_pass_false_when_threshold_exceeded(tmp / "t2")
        test_parse_error_marks_metric_and_fails(tmp / "t3")

    print("augment_status smoke tests: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
