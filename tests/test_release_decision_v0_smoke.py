#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "PULSE_safe_pack_v0" / "tools" / "materialize_release_decision.py"


POLICY_TEXT = """\
policy:
  id: pulse-gate-policy-v0-test
  version: "0.0.0"

enforcement:
  required_missing: FAIL
  required_false: FAIL
  advisory_missing: WARN
  advisory_false: WARN

gates:
  required:
    - pass_controls_refusal
    - q1_grounded_ok
  core_required:
    - pass_controls_refusal
  release_required:
    - detectors_materialized_ok
    - external_summaries_present
    - external_all_pass
  advisory:
    - external_summaries_present
    - external_all_pass
"""


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _status(
    gates: dict[str, Any],
    *,
    run_mode: str = "prod",
    diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": "status_v1",
        "created_utc": "2026-04-20T00:00:00Z",
        "metrics": {
            "run_mode": run_mode
        },
        "gates": gates,
    }
    if diagnostics is not None:
        payload["diagnostics"] = diagnostics
    return payload


def _run(
    tmp_path: Path,
    *,
    status: dict[str, Any],
    target: str,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    status_path = tmp_path / "status.json"
    policy_path = tmp_path / "pulse_gate_policy_v0.yml"
    out_path = tmp_path / "release_decision_v0.json"

    _write_json(status_path, status)
    policy_path.write_text(POLICY_TEXT, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--status",
            str(status_path),
            "--policy",
            str(policy_path),
            "--target",
            target,
            "--out",
            str(out_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert out_path.exists(), result.stdout + result.stderr
    return result, _read_json(out_path)


def test_stage_pass_requires_required_and_materialized_detectors() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-release-decision-") as tmp:
        result, decision = _run(
            Path(tmp),
            target="stage",
            status=_status(
                {
                    "pass_controls_refusal": True,
                    "q1_grounded_ok": True,
                    "detectors_materialized_ok": True
                },
                run_mode="prod",
            ),
        )

    assert result.returncode == 0, result.stdout + result.stderr
    assert decision["release_level"] == "STAGE-PASS"
    assert decision["target"] == "stage"
    assert decision["active_gate_sets"] == ["required"]
    assert decision["conditions"]["external_evidence_mode"] == "advisory"
    assert decision["blocking_reasons"] == []


def test_prod_pass_requires_required_and_release_required() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-release-decision-") as tmp:
        result, decision = _run(
            Path(tmp),
            target="prod",
            status=_status(
                {
                    "pass_controls_refusal": True,
                    "q1_grounded_ok": True,
                    "detectors_materialized_ok": True,
                    "external_summaries_present": True,
                    "external_all_pass": True
                },
                run_mode="prod",
            ),
        )

    assert result.returncode == 0, result.stdout + result.stderr
    assert decision["release_level"] == "PROD-PASS"
    assert decision["target"] == "prod"
    assert decision["active_gate_sets"] == ["required", "release_required"]
    assert decision["conditions"]["external_evidence_mode"] == "required"
    assert decision["blocking_reasons"] == []


def test_prod_fails_when_release_required_evidence_is_missing() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-release-decision-") as tmp:
        result, decision = _run(
            Path(tmp),
            target="prod",
            status=_status(
                {
                    "pass_controls_refusal": True,
                    "q1_grounded_ok": True,
                    "detectors_materialized_ok": True
                },
                run_mode="prod",
            ),
        )

    assert result.returncode == 1
    assert decision["release_level"] == "FAIL"
    assert any(
        "external_summaries_present: missing required gate" in reason
        for reason in decision["blocking_reasons"]
    )
    assert any(
        "external_all_pass: missing required gate" in reason
        for reason in decision["blocking_reasons"]
    )


def test_stage_fails_when_status_is_stubbed() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-release-decision-") as tmp:
        result, decision = _run(
            Path(tmp),
            target="stage",
            status=_status(
                {
                    "pass_controls_refusal": True,
                    "q1_grounded_ok": True,
                    "detectors_materialized_ok": True
                },
                run_mode="core",
                diagnostics={
                    "gates_stubbed": True,
                    "stub_profile": "all_true_smoke"
                },
            ),
        )

    assert result.returncode == 1
    assert decision["release_level"] == "FAIL"
    assert decision["conditions"]["stubbed"] is True
    assert any("stubbed diagnostics are present" in reason for reason in decision["blocking_reasons"])


def test_non_literal_true_gate_fails_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="pulse-release-decision-") as tmp:
        result, decision = _run(
            Path(tmp),
            target="stage",
            status=_status(
                {
                    "pass_controls_refusal": "true",
                    "q1_grounded_ok": True,
                    "detectors_materialized_ok": True
                },
                run_mode="prod",
            ),
        )

    assert result.returncode == 1
    assert decision["release_level"] == "FAIL"
    assert any(
        item["gate_id"] == "pass_controls_refusal"
        and item["present"] is True
        and item["passed"] is False
        and item["value_type"] == "string"
        for item in decision["gate_results"]
    )


def main() -> int:
    tests = [
        test_stage_pass_requires_required_and_materialized_detectors,
        test_prod_pass_requires_required_and_release_required,
        test_prod_fails_when_release_required_evidence_is_missing,
        test_stage_fails_when_status_is_stubbed,
        test_non_literal_true_gate_fails_closed,
    ]

    for test in tests:
        try:
            test()
        except AssertionError as exc:
            print(f"ERROR in {test.__name__}: {exc}")
            return 1

    print("OK: release_decision_v0 smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
