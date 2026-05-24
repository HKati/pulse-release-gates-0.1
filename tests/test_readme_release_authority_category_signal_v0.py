#!/usr/bin/env python3
"""README front-door release-authority category signal guard.

This test guards against recognition-surface drift in the README front door.

It does not test release authority.

It checks that the README first-screen / front-door section exposes the
mechanics already present in PULSE:

- structural gap between probabilistic AI behavior and deterministic software
  release permission;
- release-authority category;
- process-based trust -> evidence-state release authority;
- PULSEmech as artifact-bound, policy-declared, gate-materialized,
  CI-enforced evidence-to-decision path.

The guard is intentionally scoped to the front-door section. It is not a full
README terminology rewrite check.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


FRONT_DOOR_END_MARKERS = [
    "\n## Quickstart\n",
    "\n### What’s new\n",
]


REQUIRED_FRONT_DOOR_ANCHORS = [
    "PULSE — Artifact-Bound Release Authority for AI Release Decisions",
    "PULSE is an evolving artifact-bound release-authority field instrument",
    "PULSE fills the structural gap between probabilistic AI behavior and deterministic software release permission",
    "Release authority in PULSE is a materialized evidence state",
    "recorded release evidence is bound to `status.json`, declared gate policy, materialized required gates, and strict fail-closed CI gate enforcement",
    "the declared-policy CI outcome becomes the release decision",
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


FORBIDDEN_FRONT_DOOR_PHRASES = [
    "PULSEmech architecture map",
    "artifact-first release-governance",
    "release-governance",
    "release-governance lane",
    "release-governance workflow",
    "release-governance boundary",
    "release-governance outputs",
    "broader PULSE release-governance layer",
    "shadow layer registry",
    "Registered shadow layers remain",
    "Diagnostic layers (CI",
    "AI-specific constitutional framework",
    "governance-first release framework",
    "evidence-first release framework",
]


def _read_readme() -> str:
    return README.read_text(encoding="utf-8")


def _front_door_text() -> str:
    text = _read_readme()
    cut_points = [
        text.find(marker)
        for marker in FRONT_DOOR_END_MARKERS
        if marker in text
    ]

    if not cut_points:
        return text

    return text[: min(cut_points)]


def test_readme_front_door_contains_release_authority_category_signal() -> None:
    text = _front_door_text()

    for anchor in REQUIRED_FRONT_DOOR_ANCHORS:
        assert anchor in text, anchor


def test_readme_front_door_does_not_reintroduce_known_flattening_phrases() -> None:
    text = _front_door_text()

    for phrase in FORBIDDEN_FRONT_DOOR_PHRASES:
        assert phrase not in text, phrase


def main() -> int:
    try:
        test_readme_front_door_contains_release_authority_category_signal()
        test_readme_front_door_does_not_reintroduce_known_flattening_phrases()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: README front-door release-authority category signal guard passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
