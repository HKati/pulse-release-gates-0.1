from __future__ import annotations

from pathlib import Path

import yaml


def test_release_required_contains_expected_gates() -> None:
    policy = yaml.safe_load(Path("pulse_gate_policy_v0.yml").read_text(encoding="utf-8"))
    release_required = policy["gates"]["release_required"]

    assert "detectors_materialized_ok" in release_required
    assert "external_summaries_present" in release_required
    assert "external_all_pass" in release_required
    assert "refusal_delta_evidence_present" in release_required
