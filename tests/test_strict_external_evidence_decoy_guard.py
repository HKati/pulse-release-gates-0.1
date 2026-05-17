from __future__ import annotations

import yaml
from pathlib import Path


def test_release_required_contains_expected_gates() -> None:
    policy = yaml.safe_load(Path('pulse_gate_policy_v0.yml').read_text(encoding='utf-8'))
    rel = policy['gates']['release_required']
    assert 'detectors_materialized_ok' in rel
    assert 'external_summaries_present' in rel
    assert 'external_all_pass' in rel
    assert 'refusal_delta_evidence_present' in rel
