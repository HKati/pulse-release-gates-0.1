#!/usr/bin/env python3
"""Smoke guard for the PULSE-REF release-reference evidence packet baseline.

This test protects the non-normative baseline document from losing its
release-authority boundary anchors, packet-baseline relation anchors, current
schema-aligned builder relation anchors, and current digest-coverage wording.

It does not validate release-grade evidence.
It does not run RA1.
It does not authorize, block, override, or create release authority.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = (
    ROOT
    / "docs"
    / "PULSE_REF_RELEASE_REFERENCE_EVIDENCE_PACKET_BASELINE_v0.md"
)


REQUIRED_ANCHORS = [
    "Status: planning baseline / current baseline relation",
    "Authority status: non-normative",
    "Release-grade status: not release-grade evidence",
    "Verifier status: not a verifier",
    "Decision status: does not authorize, block, override, or create release authority",
    "This document defines the first PULSE-REF release-reference evidence packet baseline.",
    "the release-reference fixture matrix",
    "the evidence packet layout",
    "the minimum content contract",
    "The baseline now also records the current relation to the schema-aligned",
    "pass-fixture packet-builder path.",
    "A PULSE-REF release-grade reference is not merely a run.",
    "A release-grade reference is a recorded, artifact-bound, digest-backed, reconstructable evidence packet.",
    "The current baseline relation is no longer only a planning target.",
    "guarded positive release-reference fixture",
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
    "The baseline packet preserves the recorded `status.json` artifact.",
    "A release-reference evidence packet preserves and reconstructs this path.",
    "It does not replace it.",
    "The packet does not authorize release by existing.",
    "Evidence packet layout",
    "Minimum content contract",
    "Minimal content packet builder",
    "Release-reference fixture matrix",
    "Schema-aligned packet-builder checkpoint",
    "Baseline objective",
    "complete baseline target",
    "current v0",
    "reserved next-layer surfaces",
    "field/field_point_authority_map_v0.json",
    "admissibility/evidence_fold_in_admissibility_v0.json",
    "publication/publication_snapshot.json when canonical publication surface exists",
    "Baseline source candidate",
    "tests/fixtures/release_reference_v1/pass/",
    "Negative fixture relation",
    "Minimum baseline packet content",
    "Current v0 builder state",
    "reconstruction/source_expected_outcome.json",
    "external/summaries/README.md",
    "Packet identity requirements",
    "Run identity requirements",
    "Recorded status requirements",
    "Policy and registry requirements",
    "Materialized gate-set requirements",
    "CI outcome requirements",
    "Release authority manifest requirements",
    "Audit bundle requirements",
    "Digest requirements",
    "Digest coverage includes the regular payload files that the current builder",
    "records in the digest map.",
    "Minimum current v0 digest coverage includes regular payload files such as:",
    "audit/release_authority_audit_bundle/README.md",
    "audit/release_authority_audit_bundle/status.json",
    "audit/release_authority_audit_bundle/release_authority_manifest.json",
    "The current builder treats `package_manifest.json` and",
    "`digests/package_digests.json` as structural manifest / digest-manifest surfaces.",
    "They are generated and validated as packet artifacts, but they are not entries in",
    "the current `package_digests.json` artifact map.",
    "Operator handoff requirements",
    "Publication snapshot requirements",
    "Field-point authority map requirements",
    "Evidence fold-in admissibility requirements",
    "External evidence baseline relation",
    "HPC evidence baseline relation",
    "Recognition-surface baseline relation",
    "Reconstruction baseline",
    "Baseline acceptance conditions",
    "package digest manifest is present",
    "all required current digest-map payload files are digest-backed",
    "structural manifest / digest-manifest surfaces are present and valid",
    "Baseline rejection conditions",
    "package digest manifest is missing",
    "required digest-map payload files are not digest-backed",
    "structural manifest / digest-manifest surfaces are missing or invalid",
    "Relation to current schema-aligned builder",
    "This relation supersedes the older purely planning-baseline wording.",
    "Relation to future implementation",
    "The first schema-aligned implementation layer is partially realized.",
    "Current implemented bridge:",
    "Remaining possible next implementation steps:",
    "Relation to RA1",
    "Relation to fellowship / HPC validation",
    "Scope exclusions",
    "This document does not change:",
    "HPC may diagnostically test candidate decision-field behavior.",
    "PULSEmech remains the only release-authority mechanism.",
    "The schema-aligned packet builder now produces a reconstructable v0 packet",
    "candidate from the guarded positive pass fixture.",
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
    "The packet authorizes release by existing.",
    "The baseline authorizes release.",
    "HPC creates release authority.",
]


FORBIDDEN_STALE_OR_INACCURATE_ANCHORS = [
    "HPC validates the decision field.",
    "PULSEmech remains the release-authority mechanism.",
    "Status: planning baseline  ",
    "Authority status: non-normative  ",
    "Scope: PULSE-REF / release-reference fixture matrix / evidence packet baseline  ",
    "Release-grade status: not release-grade evidence  ",
    "Verifier status: not a verifier  ",
    "Decision status: does not authorize, block, override, or create release authority  ",
    "This document defines the first PULSE-REF release-reference evidence packet\nbaseline.",
    "A release-grade reference is a recorded, artifact-bound, digest-backed,\nreconstructable evidence packet.",
    "recorded status.json artifact",
    "Digest coverage includes all required current packet payload artifacts.",
    "Minimum current v0 digest coverage:\n\n- `README.md`;",
    "- `package_manifest.json`;\n- `status/status.json`;",
    "- `handoff/operator_handoff_report.json`;\n- `digests/package_digests.json`;",
    "- `digests/package_digests.json`;\n- `audit/release_authority_audit_bundle/`;",
    "package digests are present",
    "all required current packet artifacts are digest-backed",
    "package digests are missing",
    "required artifacts are not digest-backed",
]


def _read_baseline() -> str:
    return BASELINE.read_text(encoding="utf-8")


def test_baseline_file_exists() -> None:
    assert BASELINE.is_file()


def test_baseline_required_anchors_present() -> None:
    text = _read_baseline()

    for anchor in REQUIRED_ANCHORS:
        assert anchor in text, anchor


def test_baseline_does_not_claim_release_authority() -> None:
    text = _read_baseline()

    for claim in FORBIDDEN_CLAIMS:
        assert claim not in text, claim


def test_baseline_has_no_stale_or_inaccurate_anchors() -> None:
    text = _read_baseline()

    for anchor in FORBIDDEN_STALE_OR_INACCURATE_ANCHORS:
        assert anchor not in text, anchor


def test_baseline_status_block_has_no_trailing_whitespace() -> None:
    lines = _read_baseline().splitlines()

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
        test_baseline_file_exists()
        test_baseline_required_anchors_present()
        test_baseline_does_not_claim_release_authority()
        test_baseline_has_no_stale_or_inaccurate_anchors()
        test_baseline_status_block_has_no_trailing_whitespace()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF release-reference evidence packet baseline guard passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
