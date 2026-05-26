#!/usr/bin/env python3
"""Smoke guard for the PULSE-REF release-reference evidence packet baseline.

This test protects the non-normative baseline document from losing its
release-authority boundary anchors and packet-baseline relation anchors.

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
    "Status: planning baseline",
    "Authority status: non-normative",
    "Release-grade status: not release-grade evidence",
    "Verifier status: not a verifier",
    "Decision status: does not authorize, block, override, or create release authority",
    "This document defines the first PULSE-REF release-reference evidence packet baseline.",
    "the release-reference fixture matrix",
    "the evidence packet layout",
    "the minimum content contract",
    "A PULSE-REF release-grade reference is not merely a run.",
    "A release-grade reference is a recorded, artifact-bound, digest-backed, reconstructable evidence packet.",
    "recorded release evidence",
    "recorded `status.json` artifact",
    "declared gate policy",
    "materialized required gate set",
    "strict fail-closed CI gate enforcement",
    "declared-policy CI allow/block release decision",
    "A release-reference evidence packet preserves and reconstructs this path.",
    "It does not replace it.",
    "The packet does not authorize release by existing.",
    "Evidence packet layout",
    "Minimum content contract",
    "Minimal content packet builder",
    "Release-reference fixture matrix",
    "Baseline objective",
    "Baseline source candidate",
    "tests/fixtures/release_reference_v1/pass/",
    "Negative fixture relation",
    "Minimum baseline packet content",
    "Packet identity requirements",
    "Run identity requirements",
    "Recorded status requirements",
    "Policy and registry requirements",
    "Materialized gate-set requirements",
    "CI outcome requirements",
    "Release authority manifest requirements",
    "Audit bundle requirements",
    "Digest requirements",
    "Operator handoff requirements",
    "Publication snapshot requirements",
    "Field-point authority map requirements",
    "Evidence fold-in admissibility requirements",
    "External evidence baseline relation",
    "HPC evidence baseline relation",
    "Recognition-surface baseline relation",
    "Reconstruction baseline",
    "Baseline acceptance conditions",
    "Baseline rejection conditions",
    "Relation to future implementation",
    "Relation to RA1",
    "Relation to fellowship / HPC validation",
    "Scope exclusions",
    "This document does not change:",
    "HPC validates the decision field.",
    "PULSEmech remains the release-authority mechanism.",
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


def main() -> int:
    try:
        test_baseline_file_exists()
        test_baseline_required_anchors_present()
        test_baseline_does_not_claim_release_authority()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF release-reference evidence packet baseline guard passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
