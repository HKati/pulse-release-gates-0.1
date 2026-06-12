#!/usr/bin/env python3
"""Smoke guard for the PULSE-REF pass fixture to evidence packet handoff plan.

This guard protects the handoff-plan document that maps the guarded
release_reference_v1/pass fixture into the first packet-shaped evidence baseline
candidate.

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
    "Status: planning handoff / current builder relation",
    "Authority status: non-normative handoff record",
    "Release-grade status: not release-grade evidence",
    "Verifier status: not a verifier",
    "Decision status: does not authorize, block, override, or create release authority",
    "This document defines the handoff relation from the positive `release_reference_v1/pass` fixture to the first PULSE-REF evidence packet baseline candidate.",
    "The release-reference evidence packet baseline identifies the positive pass",
    "fixture as the preferred first source candidate for a packet-shaped baseline.",
    "This document records how that source candidate maps into the canonical evidence",
    "packet layout and how the current schema-aligned builder covers the current v0",
    "packet subset.",
    "The next proof state is a packet-shaped, digest-backed, reconstructable baseline candidate derived from a controlled positive release-reference fixture.",
    "The `release_reference_v1/pass` fixture proves that a controlled candidate can",
    "satisfy the release-reference completeness guard.",
    "The evidence packet handoff preserves that candidate as recorded artifact state.",
    "The current handoff relation is no longer only a future implementation plan.",
    "tests/fixtures/release_reference_v1/pass/status.json",
    "release-reference completeness guard",
    "policy-derived materialized required gates",
    "schema-aligned packet builder",
    "canonical packet artifacts",
    "schema-aligned packet validator",
    "reconstructable packet-shaped baseline candidate",
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
    "The source candidate is protected by the pass fixture packet-baseline candidate",
    "guard.",
    "docs/PULSE_REF_EVIDENCE_PACKET_LAYOUT_v0.md",
    "pulse_ref_evidence_packet_v0/",
    "Source-to-packet mapping",
    "Status artifact handoff",
    "Expected outcome handoff",
    "Policy handoff",
    "Registry handoff",
    "Materialized gate-set handoff",
    "The materialized gate-set artifact records the current schema-aligned v0 fields:",
    "`policy_path`",
    "`policy_sha256`",
    "`sets`",
    "`effective_required_gates`",
    "CI outcome handoff",
    "The artifact preserves the current schema-aligned v0 fields:",
    "`gate_check_job`",
    "`gate_check_conclusion`",
    "Effective required gates are recorded in `gates/materialized_gate_sets.json`.",
    "Detailed command replay is recorded in `handoff/operator_handoff_report.json`.",
    "Declared decision reconstruction is recorded in",
    "`release_authority/release_authority_manifest.json`.",
    "Release authority manifest handoff",
    "Audit bundle handoff",
    "Current v0 audit bundle files:",
    "audit/release_authority_audit_bundle/README.md",
    "audit/release_authority_audit_bundle/status.json",
    "audit/release_authority_audit_bundle/release_authority_manifest.json",
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
    "Current implemented bridge",
    "Relation to minimal content packet builder",
    "Relation to RA1",
    "Relation to fellowship / HPC validation",
    "Scope exclusions",
    "This document does not change:",
    "HPC may diagnostically test candidate decision-field behavior.",
    "PULSEmech remains the only release-authority mechanism.",
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
    "`audit/release_authority_audit_bundle/README.md`",
    "`audit/release_authority_audit_bundle/status.json`",
    "`audit/release_authority_audit_bundle/release_authority_manifest.json`",
    "`package_manifest.json`",
    "`digests/package_digests.json`",
    "`handoff/operator_handoff_report.json`",
    "`publication/publication_snapshot.json`",
    "`field/field_point_authority_map_v0.json`",
    "`admissibility/evidence_fold_in_admissibility_v0.json`",
    "`external/summaries/README.md`",
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

FORBIDDEN_STALE_OR_INACCURATE_ANCHORS = [
    "HPC validates the decision field.",
    "PULSEmech remains the release-authority mechanism.",
    "This document defines the handoff plan from the positive `release_reference_v1/pass` fixture to the first PULSE-REF evidence packet baseline candidate.",
    "This document defines how that source candidate should be mapped into the canonical evidence packet layout before any builder implementation changes are made.",
    "Implementation sequence",
    "before any builder implementation changes are made",
    "This document does not build an evidence packet.",
    "It defines the artifact mapping and handoff boundary for the next implementation step.",
    "The handoff succeeds when a future implementation can produce a packet directory",
    "The next implementation should proceed conservatively.",
    "Suggested sequence:",
    "write field-point authority map",
    "write evidence fold-in admissibility",
    "preserved status + manifest + report card",
    "selected lane or policy scope",
    "duplicate-handling rule",
    "ordering rule",
]

FORBIDDEN_CI_OUTCOME_SECTION_ANCHORS = [
    "gate-check command",
    "effective required gate set",
    "expected allow/block outcome",
    "fail-closed indicator",
]


def _read_plan() -> str:
    return PLAN.read_text(encoding="utf-8")


def _section(text: str, start_heading: str, end_heading: str) -> str:
    start = text.index(start_heading)
    end = text.index(end_heading, start)
    return text[start:end]


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


def test_handoff_plan_has_no_stale_or_inaccurate_anchors() -> None:
    text = _read_plan()

    for anchor in FORBIDDEN_STALE_OR_INACCURATE_ANCHORS:
        assert anchor not in text, anchor


def test_ci_outcome_section_does_not_claim_fields_owned_by_other_artifacts() -> None:
    text = _read_plan()
    section = _section(
        text,
        "## CI outcome handoff",
        "## Release authority manifest handoff",
    )

    for anchor in FORBIDDEN_CI_OUTCOME_SECTION_ANCHORS:
        assert anchor not in section, anchor


def test_release_authority_manifest_section_may_reference_fail_closed_indicator() -> None:
    text = _read_plan()
    section = _section(
        text,
        "## Release authority manifest handoff",
        "## Audit bundle handoff",
    )

    assert "fail-closed indicator" in section


def test_handoff_plan_status_block_has_no_trailing_whitespace() -> None:
    lines = _read_plan().splitlines()

    protected_prefixes = (
        "Status:",
        "Authority status:",
        "Scope:",
        "Release-grade status:",
        "Verifier status:",
        "Decision status:",
    )

    for line in lines:
        if line.startswith(protected_prefixes):
            assert line == line.rstrip(), line


def main() -> int:
    try:
        test_handoff_plan_file_exists()
        test_handoff_plan_required_anchors_present()
        test_handoff_plan_mapping_anchors_present()
        test_handoff_plan_does_not_claim_release_authority()
        test_handoff_plan_has_no_stale_or_inaccurate_anchors()
        test_ci_outcome_section_does_not_claim_fields_owned_by_other_artifacts()
        test_release_authority_manifest_section_may_reference_fail_closed_indicator()
        test_handoff_plan_status_block_has_no_trailing_whitespace()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF pass fixture to evidence packet handoff plan guard passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
