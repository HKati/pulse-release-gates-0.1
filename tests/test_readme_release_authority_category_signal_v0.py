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
  CI-enforced evidence-to-decision path;
- the completed public hosted release-grade reference-run identity.

The guard is intentionally scoped to the front-door section. It is not a full
README terminology rewrite check.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


FRONT_DOOR_END_MARKERS = [
    "\n## Quickstart\n",
    "\n### What’s new\n",
]


REQUIRED_FRONT_DOOR_ANCHORS = [
    (
        "PULSE — Artifact-Bound Release Authority "
        "for AI Release Decisions"
    ),
    "Canonical PULSEmech implementation path",
    (
        "PULSEmech is the artifact-bound "
        "release-authority mechanism for AI "
        "release decisions"
    ),
    "recorded current-run release evidence",
    "canonical candidate production",
    "canonical candidate replay",
    "recorded release-evidence verification",
    "canonical verifier replay",
    (
        "policy-derived release-required gate "
        "materialization"
    ),
    (
        "workflow-effective materialized required "
        "gate set"
    ),
    "PULSE_safe_pack_v0/tools/check_gates.py",
    "primary CI allow/block release decision",
    (
        "PULSE is an artifact-bound release-authority "
        "system for AI applications and AI-enabled "
        "systems"
    ),
    (
        "PULSE fills the structural gap between "
        "probabilistic AI behavior and deterministic "
        "software release permission"
    ),
    (
        "The evidence-producing surfaces for PULSE "
        "include AI applications, model behavior, "
        "evaluation suites, detector systems, review "
        "processes, logs, dashboards, and deployment "
        "pipelines"
    ),
    (
        "These surfaces produce, record, or render "
        "candidate release evidence"
    ),
    (
        "PULSE materializes recorded current-run "
        "release evidence into artifact-bound release "
        "state before deployment"
    ),
    (
        "The release-required materializer admits "
        "only verifier-bound, policy-derived gate state"
    ),
    "It does not independently decide release",
    (
        "Release permission is produced only by the "
        "complete connected path"
    ),
    (
        "The declared-policy primary CI outcome is "
        "the recorded terminal enforcement result "
        "of that path"
    ),
    (
        "Release authority in PULSE is a connected, "
        "materialized evidence state"
    ),
    "probabilistic AI behavior",
    "recorded candidate release evidence",
    "artifact-bound release-authority state",
    "deterministic software release permission",
    "PULSEmech is the mechanism",
    (
        "artifact-bound, policy-declared, "
        "gate-materialized, CI-enforced "
        "evidence-to-decision path"
    ),
    "PULSEmech release-authority materialization map",
    (
        "release-grade PULSE reference is not merely "
        "a run"
    ),
    (
        "closed, digest-backed, reconstructable "
        "evidence packet"
    ),
    "Completed public non-stubbed release-grade run record",
    "PULSE CI #6066",
    "46b639706e23f80fe296a8893be18e2b5ab21f7e",
    "RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md",
    "hosted_full_runtime",
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
    (
        "Release authority in PULSE is a "
        "materialized evidence state"
    ),
    (
        "PULSE materializes recorded candidate "
        "release evidence into artifact-bound "
        "release-authority state before deployment"
    ),
    (
        "Release permission is produced by the "
        "complete materialization path"
    ),
    (
        "The declared-policy gate-enforcement CI "
        "outcome is the release decision."
    ),
    "\n→ check_gates.py\n",
    "\n+ check_gates.py\n",
    "pending template; not a completed run record",
    "Pending controlled hosted execution",
]


def _read_readme() -> str:
    return README.read_text(encoding="utf-8")


def _normalize_readme_category_signal(text: str) -> str:
    return re.sub(
        r'<img\b[^>]*\balt="([^"]+)"[^>]*>',
        r"\1",
        text,
    )


def _front_door_text() -> str:
    text = _normalize_readme_category_signal(_read_readme())
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

    print(
        "OK: README front-door release-authority category signal "
        "guard passed"
    )
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
