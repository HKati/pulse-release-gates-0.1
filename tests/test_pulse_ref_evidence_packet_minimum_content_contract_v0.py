#!/usr/bin/env python3
"""Smoke guard for the PULSE-REF evidence packet minimum content contract.

This test protects the non-normative planning contract from being truncated or
losing its release-authority boundary anchors.

It does not validate release-grade evidence.

It does not run RA1.

It does not authorize, block, override, or create release authority.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "PULSE_REF_EVIDENCE_PACKET_MINIMUM_CONTENT_CONTRACT_v0.md"


REQUIRED_ANCHORS = [
    "Status: planning contract",
    "Authority status: non-normative",
    "Release-grade status: not release-grade evidence",
    "Verifier status: not a verifier",
    "Decision status: does not authorize, block, override, or create release authority",
    "A PULSE-REF evidence packet is not merely a run.",
    "A PULSE-REF evidence packet is a closed, digest-backed, reconstructable evidence field.",
    "recorded release evidence",
    "status.json",
    "declared gate policy",
    "materialized required gate set",
    "strict fail-closed CI gate enforcement",
    "declared-policy CI allow/block release decision",
    "layout skeleton",
    "minimum content contract",
    "release-grade evidence packet",
    "release authority",
    "Minimum packet identity content",
    "Minimum run identity content",
    "Minimum status artifact content",
    "Minimum policy and registry content",
    "Minimum materialized gate-set content",
    "Minimum CI outcome content",
    "Minimum release-authority manifest content",
    "Minimum audit bundle content",
    "Minimum package digest content",
    "Minimum operator handoff content",
    "Minimum publication snapshot content",
    "Minimum reconstruction instructions",
    "Optional external evidence content",
    "Optional HPC evidence content",
    "Optional recognition-surface evidence content",
    "Field-point authority classification",
    "Evidence fold-in admissibility content",
    "Minimum negative conditions",
    "Minimum positive conditions",
    "Relation to future checkers",
    "Relation to RA1 verifier",
    "Scope exclusions",
    "This document does not change:",
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
]


def _read_contract() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def test_minimum_content_contract_file_exists() -> None:
    assert CONTRACT.is_file()


def test_minimum_content_contract_required_anchors_present() -> None:
    text = _read_contract()

    for anchor in REQUIRED_ANCHORS:
        assert anchor in text, anchor


def test_minimum_content_contract_does_not_claim_release_authority() -> None:
    text = _read_contract()

    for claim in FORBIDDEN_CLAIMS:
        assert claim not in text, claim


def main() -> int:
    try:
        test_minimum_content_contract_file_exists()
        test_minimum_content_contract_required_anchors_present()
        test_minimum_content_contract_does_not_claim_release_authority()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF minimum content contract guard passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
