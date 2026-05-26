#!/usr/bin/env python3
"""Smoke guard for the release_reference_v1/pass packet-baseline candidate.

This test protects the selected positive release-reference fixture that will
serve as the first source candidate for a future PULSE-REF evidence packet
baseline.

It does not build an evidence packet.

It does not validate release-grade evidence.

It does not run RA1.

It does not authorize, block, override, or create release authority.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "release_reference_v1" / "pass"
STATUS = FIXTURE_DIR / "status.json"
EXPECTED_OUTCOME = FIXTURE_DIR / "expected_outcome.json"


BASELINE_CRITICAL_GATES = [
    "pass_controls_refusal",
    "refusal_delta_pass",
    "refusal_delta_evidence_present",
    "pass_controls_sanit",
    "sanitization_effective",
    "q1_grounded_ok",
    "q4_slo_ok",
    "detectors_materialized_ok",
    "external_summaries_present",
    "external_all_pass",
]


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), path
    return data


def test_pass_fixture_files_exist() -> None:
    assert STATUS.is_file()
    assert EXPECTED_OUTCOME.is_file()


def test_pass_fixture_identity_is_positive_release_reference() -> None:
    status = _load_json(STATUS)

    metrics = status.get("metrics")
    assert isinstance(metrics, dict)

    assert metrics.get("run_mode") == "prod"
    assert metrics.get("fixture_id") == "release_reference_v1/pass"
    assert metrics.get("fixture_kind") == "positive_release_reference"


def test_pass_fixture_is_explicitly_non_stubbed_and_non_scaffolded() -> None:
    status = _load_json(STATUS)

    diagnostics = status.get("diagnostics")
    assert isinstance(diagnostics, dict)

    assert diagnostics.get("gates_stubbed") is False
    assert diagnostics.get("scaffold") is False


def test_pass_fixture_baseline_critical_gates_are_literal_true() -> None:
    status = _load_json(STATUS)

    gates = status.get("gates")
    assert isinstance(gates, dict)

    for gate in BASELINE_CRITICAL_GATES:
        assert gates.get(gate) is True, gate


def test_pass_fixture_all_recorded_gates_are_literal_true() -> None:
    status = _load_json(STATUS)

    gates = status.get("gates")
    assert isinstance(gates, dict)
    assert gates

    for gate, value in gates.items():
        assert value is True, f"{gate}={value!r}"


def test_pass_fixture_evidence_surfaces_are_materialized() -> None:
    status = _load_json(STATUS)

    evidence = status.get("evidence")
    assert isinstance(evidence, dict)

    assert evidence.get("detectors_materialized") is True
    assert evidence.get("external_summaries_present") is True
    assert evidence.get("external_summary_mode") == "fixture"


def test_pass_fixture_expected_outcome_declares_pass() -> None:
    expected = _load_json(EXPECTED_OUTCOME)

    assert expected.get("fixture_id") == "release_reference_v1/pass"
    assert expected.get("expected_result") == "PASS"
    assert expected.get("expected_guard") == "ci/check_release_reference_complete_v1.py"

    checks = expected.get("expected_checks")
    assert isinstance(checks, dict)

    assert checks.get("run_mode") == "prod"
    assert checks.get("gates_stubbed") is False
    assert checks.get("detectors_materialized_ok") is True
    assert checks.get("external_summaries_present") is True
    assert checks.get("external_all_pass") is True
    assert checks.get("required_gates_literal_true") is True
    assert checks.get("release_required_gates_literal_true") is True


def test_pass_fixture_does_not_claim_release_authority() -> None:
    status = _load_json(STATUS)
    expected = _load_json(EXPECTED_OUTCOME)

    evidence = status.get("evidence")
    assert isinstance(evidence, dict)

    status_boundary = evidence.get("authority_boundary")
    expected_boundary = expected.get("authority_boundary")

    assert isinstance(status_boundary, str)
    assert isinstance(expected_boundary, str)

    assert "does not create release authority" in status_boundary
    assert "does not define release authority" in expected_boundary


def main() -> int:
    try:
        test_pass_fixture_files_exist()
        test_pass_fixture_identity_is_positive_release_reference()
        test_pass_fixture_is_explicitly_non_stubbed_and_non_scaffolded()
        test_pass_fixture_baseline_critical_gates_are_literal_true()
        test_pass_fixture_all_recorded_gates_are_literal_true()
        test_pass_fixture_evidence_surfaces_are_materialized()
        test_pass_fixture_expected_outcome_declares_pass()
        test_pass_fixture_does_not_claim_release_authority()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: release_reference_v1/pass packet-baseline candidate guard passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
