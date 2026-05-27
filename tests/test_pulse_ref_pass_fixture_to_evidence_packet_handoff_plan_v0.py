#!/usr/bin/env python3
"""Smoke guard for the PULSE-REF pass fixture to evidence packet handoff plan.

This guard protects the handoff-plan document that maps the guarded
release_reference_v1/pass fixture into the first packet-shaped evidence
baseline candidate.

It is a documentation contract guard.

It does not build an evidence packet.

It does not validate release-grade evidence.

It does not run RA1.

It does not authorize, block, override, or create release authority.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = (
    ROOT
    / "docs"
    / "PULSE_REF_PASS_FIXTURE_TO_EVIDENCE_PACKET_HANDOFF_PLAN_v0.md"
)


REQUIRED_ANCHORS = [
    "Status: planning handoff",
    "Authority status: non-normative",
    "Release-grade status: not release-grade evidence",
    "Verifier status: not a verifier",
    "Decision status: does not authorize, block, override, or create release authority",
    "This document defines the handoff plan from the positive `release_reference_v1/pass` fixture to the first PULSE-REF evidence packet baseline candidate.",
    "The release-reference evidence packet baseline identifies the positive pass fixture as the preferred first source candidate for a packet-shaped baseline.",
    "This document defines how that source candidate should be mapped into the canonical evidence packet layout before any builder implementation changes are made.",
    "The next proof state is a packet-shaped, digest-backed, reconstructable baseline candidate derived from a controlled positive release-reference fixture.",
    "The `release_reference_v1/pass` fixture proves that a controlled candidate can satisfy the release-reference completeness guard.",
    "The evidence packet handoff must preserve that candidate as recorded artifact state.",
    "recorded release evidence",
    "recorded `status.json` artifact",
    "declared gate policy",
    "materialized required gate set",
    "strict fail-closed CI gate enforcement",
    "declared-policy CI allow/block release decision",
    "tests/fixtures/release_reference_v1/pass/",
    "status.json",
    "expected_outcome.json",
    'metrics.run_mode = "prod"',
    'metrics.fixture_id = "release_reference_v1/pass"',
    'metrics.fixture_kind = "positive_release_reference"',
    "diagnostics.gates_stubbed = false",
    "diagnostics.scaffold = false",
    "required gates literal boolean `true`",
    "release_required gates literal boolean `true`",
    "detector evidence materialized",
    "external summaries present",
    "external aggregate passing",
    "expected outcome `PASS`",
    "The source candidate is protected by the pass fixture packet-baseline candidate guard.",
    "docs/PULSE_REF_EVIDENCE_PACKET_LAYOUT_v0.md",
    "pulse_ref_evidence_packet_v0/",
    "Source-to-packet mapping",
    "Status artifact handoff",
    "Expected outcome handoff",
    "Policy handoff",
    "Registry handoff",
    "Materialized gate-set handoff",
    "CI outcome handoff",
    "Release authority manifest handoff",
    "Audit bundle handoff",
    "Digest handoff",
    "Operator handoff report",
    "Publication snapshot",
    "Field-point authority map",
    "Evidence fold-in admissibility",
    "External evidence relation",
    "HPC evidence relation",
    "Recognition-surface relation",
    "Reconstruction instructions",
    "Acceptance conditions",
    "Rejection conditions",
    "Implementation sequence",
    "Relation to minimal content packet builder",
    "Relation to RA1",
    "Relation to fellowship / HPC validation",
    "Scope exclusions",
    "This document does not change:",
    "HPC validates the decision field.",
    "PULSEmech remains the release-authority mechanism.",
]


REQUIRED_MAPPING_ANCHORS = [
    "`tests/fixtures/release_reference_v1/pass/status.json`",
    "`status/status.json`",
    "`tests/fixtures/release_reference_v1/pass/expected_outcome.json`",
    "`reconstruction/source_expected_outcome.json`",
    "`pulse_gate_policy_v0.yml`",
    "`policy/pulse_gate_policy_v0.yml`",
    "`pulse_gate_registry_v0.yml`",
    "`policy/pulse_gate_registry_v0.yml`",
    "`gates/materialized_gate_sets.json`",
    "`ci/ci_outcome.json`",
    "`release_authority/release_authority_manifest.json`",
    "`audit/release_authority_audit_bundle/`",
    "`package_manifest.json`",
    "`digests/package_digests.json`",
    "`handoff/operator_handoff_report.json`",
    "`publication/publication_snapshot.json`",
    "`field/field_point_authority_map_v0.json`",
    "`admissibility/evidence_fold_in_admissibility_v0.json`",
    "`external/summaries/`",
    "`hpc/hpc_evidence_bundle_v0.json`",
    "`recognition/recognition_surface_drift_v0.json`",
    "`reconstruction/reconstruction_instructions.md`",
]


FORBIDDEN_CLAIMS = [
    "This document creates release authority.",
    "This document authorizes release authority.",
    "This document blocks release authority.",
    "This document overrides release authority.",
    "This document validates release-grade evidence.",
    "This document runs RA1.",
    "This document replaces RA1.",
    "This document relaxes RA1.",
    "The handoff plan creates release authority.",
    "The handoff plan authorizes release.",
    "The packet candidate authorizes release by existing.",
    "HPC creates release authority.",
]


def _read_plan() -> str:
    return PLAN.read_text(encoding="utf-8")


def test_handoff_plan_file_exists() -> None:
    assert PLAN.is_file()


def test_handoff_plan_required_anchors_present() -> None:
    text = _read_plan()

    for anchor in REQUIRED_ANCHORS:
        assert anchor in text, anchor


def test_handoff_plan_mapping_anchors_present() -> None:
    text = _read_plan()

    for anchor in REQUIRED_MAPPING_ANCHORS:
        assert anchor in text, anchor


def test_handoff_plan_does_not_claim_release_authority() -> None:
    text = _read_plan()

    for claim in FORBIDDEN_CLAIMS:
        assert claim not in text, claim


def main() -> int:
    try:
        test_handoff_plan_file_exists()
        test_handoff_plan_required_anchors_present()
        test_handoff_plan_mapping_anchors_present()
        test_handoff_plan_does_not_claim_release_authority()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF pass fixture to evidence packet handoff plan guard passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
