#!/usr/bin/env python3
"""Smoke guard for the PULSE-REF schema-aligned packet builder contract.

This guard protects the contract that must be satisfied before reintroducing
the pass-fixture evidence packet baseline builder.

It is a documentation contract guard.

It does not build an evidence packet.

It does not validate release-grade evidence.

It does not run RA1.

It does not authorize, block, override, or create release authority.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "docs"
    / "PULSE_REF_SCHEMA_ALIGNED_PASS_FIXTURE_PACKET_BUILDER_CONTRACT_v0.md"
)


REQUIRED_ANCHORS = [
    "Status: builder contract",
    "Authority status: non-normative implementation contract",
    "Scope: PULSE-REF / pass fixture / evidence packet baseline builder / schema-aligned packet artifacts",
    "Release-grade status: packet-baseline preparation contract",
    "Verifier status: pre-verifier contract",
    "Decision status: preserves the declared PULSEmech release-authority path",
    "This document defines the schema-aligned builder contract",
    "The contract exists before reintroducing the builder implementation.",
    "The builder may generate a packet-shaped baseline candidate only when each canonical packet path receives a payload that matches its declared artifact contract.",
    "source fixture",
    "recorded packet artifact",
    "canonical packet path",
    "schema-aligned payload",
    "reconstructable evidence packet baseline",
    "It does not reduce PULSE to a schema package.",
    "PULSE is an artifact-bound release-authority system.",
    "PULSEmech remains the mechanism:",
    "recorded release evidence",
    "recorded `status.json` artifact",
    "declared gate policy",
    "materialized required gate set",
    "strict fail-closed CI gate enforcement",
    "declared-policy CI allow/block release decision",
    "A packet builder operates below that mechanism as an artifact-preparation surface.",
    "Schema alignment protects the packet from artifact drift.",
    "Schema alignment does not define PULSE.",
    "Contract principle",
    "A canonical packet path carries a canonical artifact contract.",
    "Canonical path rule",
    "Source fixture contract",
    "Declared policy materialization contract",
    "Status artifact contract",
    "Expected outcome contract",
    "CI outcome contract",
    "Package digest contract",
    "Package manifest contract",
    "Release authority manifest contract",
    "Operator handoff report contract",
    "Publication snapshot contract",
    "Optional surface contract",
    "Fixture-specific payload rule",
    "Builder acceptance conditions",
    "Builder rejection conditions",
    "Relation to RA1",
    "Relation to PULSE identity",
    "Relation to fellowship / HPC validation",
    "Scope exclusions",
    "Closing statement",
    "HPC validates the decision field.",
    "PULSEmech remains the release-authority mechanism.",
]


CANONICAL_PATH_ANCHORS = [
    "`status/status.json`",
    "`policy/pulse_gate_policy_v0.yml`",
    "`policy/pulse_gate_registry_v0.yml`",
    "`gates/materialized_gate_sets.json`",
    "`ci/ci_outcome.json`",
    "`release_authority/release_authority_manifest.json`",
    "`package_manifest.json`",
    "`digests/package_digests.json`",
    "`handoff/operator_handoff_report.json`",
    "`publication/publication_snapshot.json`",
    "`field/field_point_authority_map_v0.json`",
    "`admissibility/evidence_fold_in_admissibility_v0.json`",
    "`reconstruction/reconstruction_instructions.md`",
]


SCHEMA_ALIGNMENT_ANCHORS = [
    "The builder must derive materialized gate sets from the declared policy.",
    "The builder must not infer the required/release_required split only from `status.gates` plus a hard-coded release_required list.",
    "canonical `pulse_ref_ci_outcome_v0` artifact",
    "canonical package digest shape",
    "`pulse_ref_package_digests_v0`",
    "verifier-readable package manifest",
    "named artifact references",
    "canonical release authority manifest shape",
    "run identity",
    "inputs",
    "authority",
    "evaluation",
    "canonical operator handoff schema",
    "`ok`",
    "`repo_root`",
    "`gate_mode`",
    "`status_source`",
    "`effective_required_gates`",
    "`files`",
    "`commands`",
    "`warnings`",
    "`errors`",
    "omit `publication/publication_snapshot.json`",
    "emit a canonical publication snapshot payload",
]


REJECTION_ANCHORS = [
    "materialized gates are inferred from status alone while presented as declared-policy materialization",
    "hard-coded gate promotion is used without policy-derived materialization",
    "a canonical path receives fixture-specific schema",
    "package manifest lacks named artifact references",
    "package digests use non-canonical digest structure",
    "CI outcome lacks canonical run/conclusion fields",
    "release authority manifest lacks canonical run/input/authority/evaluation sections",
    "operator handoff lacks required reconstruction fields",
    "publication snapshot is included with non-canonical shape",
    "optional diagnostic surfaces are presented as release-authority surfaces",
    "generated packet cannot be consumed by existing schema/verifier tooling",
]


FORBIDDEN_CLAIMS = [
    "This contract creates release authority.",
    "This contract authorizes release authority.",
    "This contract blocks release authority.",
    "This contract overrides release authority.",
    "This contract validates release-grade evidence.",
    "This contract runs RA1.",
    "This contract replaces RA1.",
    "This contract relaxes RA1.",
    "Schema alignment is the identity of PULSE.",
    "PULSE is a schema package.",
    "The builder creates release authority.",
    "HPC creates release authority.",
]


def _read_contract() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def test_schema_aligned_contract_file_exists() -> None:
    assert CONTRACT.is_file()


def test_schema_aligned_contract_required_anchors_present() -> None:
    text = _read_contract()

    for anchor in REQUIRED_ANCHORS:
        assert anchor in text, anchor


def test_schema_aligned_contract_canonical_path_anchors_present() -> None:
    text = _read_contract()

    for anchor in CANONICAL_PATH_ANCHORS:
        assert anchor in text, anchor


def test_schema_aligned_contract_schema_alignment_anchors_present() -> None:
    text = _read_contract()

    for anchor in SCHEMA_ALIGNMENT_ANCHORS:
        assert anchor in text, anchor


def test_schema_aligned_contract_rejection_anchors_present() -> None:
    text = _read_contract()

    for anchor in REJECTION_ANCHORS:
        assert anchor in text, anchor


def test_schema_aligned_contract_does_not_claim_release_authority() -> None:
    text = _read_contract()

    for claim in FORBIDDEN_CLAIMS:
        assert claim not in text, claim


def main() -> int:
    try:
        test_schema_aligned_contract_file_exists()
        test_schema_aligned_contract_required_anchors_present()
        test_schema_aligned_contract_canonical_path_anchors_present()
        test_schema_aligned_contract_schema_alignment_anchors_present()
        test_schema_aligned_contract_rejection_anchors_present()
        test_schema_aligned_contract_does_not_claim_release_authority()
    except AssertionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: PULSE-REF schema-aligned packet builder contract guard passed")
    return 0


def test_smoke() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
