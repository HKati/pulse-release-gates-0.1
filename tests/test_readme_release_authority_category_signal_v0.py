#!/usr/bin/env python3
"""README release-authority category signal guard.

This test guards against recognition-surface drift in the README front door.

It does not test release authority.

It checks that the README exposes the mechanics already present in PULSE:

- structural gap between probabilistic AI behavior and deterministic software
  release permission;
- release-authority category;
- process-based trust -> evidence-state release authority;
- PULSEmech as artifact-bound, policy-declared, gate-materialized,
  CI-enforced evidence-to-decision path.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


REQUIRED_README_ANCHORS = [
    "PULSE — Artifact-Bound Release Authority for AI Release Decisions",
    "PULSE is an evolving artifact-bound release-authority field instrument",
    "PULSE fills the structural gap between probabilistic AI behavior and deterministic software release permission",
    "PULSE defines a release-authority category for AI releases",
    "release permission is not inferred from scores, dashboards, reports, governance review, or pipeline success",
    "PULSE breaks from process-based trust to evidence-state release authority",
    "PULSEmech is the mechanism",
    "artifact-bound, policy-declared, gate-materialized, CI-enforced evidence-to-decision path",
    "The declared-policy gate-enforcement CI outcome is the release decision.",
    "PULSEmech release-authority materialization map",
    "recorded release evidence",
    "status.json",
    "declared gate policy",
    "materialized required gate set",
    "strict fail-closed CI gate enforcement",
    "release-grade PULSE reference is not merely a run",
    "closed, digest-backed, reconstructable evidence packet",
]

FORBIDDEN_README_PHRASES = [
    "PULSEmech architecture map",
    "artifact-first release-governance",
    "release-governance",
    "release-governance lane",
    "release-governance workflow",
    "release-governance boundary",
    "release-governance outputs",
    "broader PULSE release-governance layer",
    "shadow layer registry",
    "shadow layer",
    "shadow layers",
    "diagnostic layers",
    "AI-specific constitutional framework",
    "governance-first release framework",
    "evidence-first release framework",
]


def _read_readme() -> str:
    return README.read_text(encoding="utf-8")


def test_readme_contains_release_authority_category_signal() -> None:
    text = _read_readme()

    for anchor in REQUIRED_README_ANCHORS:
        assert anchor in text, anchor


def test_readme_does_not_reintroduce_known_flattening_phrases() -> None:
    text = _read_readme()

    for phrase in FORBIDDEN_README_PHRASES:
        assert phrase not in text, phrase


def main() -> int:
    try:
        test_readme_contains_release_authority_category_signal()
        test_readme_does_not_reintroduce_known_flattening_phrases()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: README release-authority category signal guard passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
