from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
EXAMPLE_DIR = ROOT / "examples" / "anchor_integrity_v0_1"
BASELINE = ROOT / "contracts" / "anchor_integrity_v0_1_baseline_inventory.json"
CONTRACT_DOC = ROOT / "docs" / "ANCHOR_INTEGRITY_v0_1_CONTRACT.md"
TEST_PATH = "tests/test_anchor_integrity_v0_1_contract.py"

SCHEMA_EXAMPLE_PAIRS = {
    "anchor_integrity_claim_packet_v0_1.schema.json": "claim_packet.example.json",
    "anchor_integrity_evidence_packet_v0_1.schema.json": "evidence_packet.example.json",
    "anchor_integrity_relation_verification_packet_v0_1.schema.json": (
        "relation_verification_packet.example.json"
    ),
    "anchor_integrity_input_v0_1.schema.json": "anchor_integrity_input.example.json",
    "anchor_integrity_output_v0_1.schema.json": "anchor_integrity_output.example.json",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validator(schema_name: str) -> jsonschema.Draft202012Validator:
    schema = load_json(SCHEMA_DIR / schema_name)
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def validation_errors(schema_name: str, payload: dict) -> list[jsonschema.ValidationError]:
    return sorted(
        validator(schema_name).iter_errors(payload),
        key=lambda error: [str(part) for part in error.absolute_path],
    )


def assert_valid(schema_name: str, payload: dict) -> None:
    errors = validation_errors(schema_name, payload)
    assert not errors, [
        {"path": list(error.absolute_path), "message": error.message}
        for error in errors
    ]


def assert_invalid(schema_name: str, payload: dict) -> None:
    errors = validation_errors(schema_name, payload)
    assert errors, "payload unexpectedly validated"


def example(name: str) -> dict:
    return load_json(EXAMPLE_DIR / name)


@pytest.mark.parametrize("schema_name", sorted(SCHEMA_EXAMPLE_PAIRS))
def test_schema_is_valid_draft_2020_12(schema_name: str) -> None:
    schema = load_json(SCHEMA_DIR / schema_name)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    jsonschema.Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize(
    ("schema_name", "example_name"),
    sorted(SCHEMA_EXAMPLE_PAIRS.items()),
)
def test_positive_example_validates(schema_name: str, example_name: str) -> None:
    assert_valid(schema_name, example(example_name))


def test_baseline_inventory_is_bound_to_reviewed_main_source() -> None:
    inventory = load_json(BASELINE)
    assert inventory["schema_version"] == "anchor_integrity_v0_1_baseline_inventory"
    assert inventory["source_repository"] == "HKati/pulse-release-gates-0.1"
    assert inventory["source_branch"] == "main"
    assert inventory["source_commit"] == (
        "34431ec8ebe305a83273ffd39b78f083219f03e6"
    )
    assert inventory["source_tree"] == "937ec96441a5f9c3209b43c70c04d389e1a5b679"
    assert inventory["candidate_status"] == "diagnostic_only"
    assert inventory["authority_effect"] == "none"
    assert inventory["release_authority_activation"] is False

    expected_blobs = {
        "docs/ANCHOR_INTEGRITY_v0.md": "31188dfe1a33012d8869f035612d4d3e98515e0a",
        "schemas/anchor_integrity_v0.schema.json": (
            "a67472be9fa0415d33374204125ea4785d5bb4c6"
        ),
        "scripts/anchor_integrity_adapter_v0.py": (
            "3f4afe26be361fddda153f72dd20803183a85a8e"
        ),
        "scripts/check_anchor_integrity_v0_contract.py": (
            "023e3a6e817cc1c1967cf7926763fe9837b6f26e"
        ),
        "scripts/render_anchor_integrity_overlay_v0_md.py": (
            "73ec5aeabeb05d6018be62fa79954e1c73dfe0a9"
        ),
    }
    observed_blobs = {
        row["path"]: row["git_blob_sha1"]
        for row in inventory["v0_source_files"]
    }
    assert observed_blobs == expected_blobs

    gap_ids = {row["gap_id"] for row in inventory["observed_semantic_gaps"]}
    assert gap_ids == {
        "legacy_proxy_not_claim_coverage",
        "cycle_check_not_implemented",
        "claim_evidence_relation_not_materialized",
    }


def test_contract_document_fixes_the_authority_boundary() -> None:
    text = CONTRACT_DOC.read_text(encoding="utf-8")
    assert "**Authority effect:** `none`" in text
    assert "**Release-authority activation:** `false`" in text
    assert "legacy gate-signal ratio" in text
    assert "status != completed" in text
    assert "result = null" in text
    assert "Work package 1 does not implement the detector" in text
    assert "No hallucination-reduction percentage" in text


def _manifest_entries(path: Path) -> list[str]:
    entries: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    return entries


def test_contract_test_is_registered_exactly_once_in_both_manifests() -> None:
    for relative in ("ci/pytest-tests.list", "ci/tools-tests.list"):
        entries = _manifest_entries(ROOT / relative)
        assert entries.count(TEST_PATH) == 1, relative


def test_legacy_proxy_cannot_be_relabelled_as_claim_evidence_coverage() -> None:
    payload = example("anchor_integrity_output.example.json")
    payload["legacy_signal_summary"]["is_claim_evidence_coverage"] = True
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_input_legacy_proxy_cannot_be_relabelled_as_claim_evidence_coverage() -> None:
    payload = example("anchor_integrity_input.example.json")
    payload["legacy_overlay"]["is_claim_evidence_coverage"] = True
    assert_invalid("anchor_integrity_input_v0_1.schema.json", payload)


def test_non_run_cycle_check_requires_null_result_and_algorithm() -> None:
    payload = example("anchor_integrity_output.example.json")
    cycle = payload["checks"]["cycle_check"]
    cycle["result"] = "no_unanchored_cycle_detected"
    cycle["algorithm"] = "typed_scc_anchor_v0_1"
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_low_is_not_a_cycle_check_result() -> None:
    payload = example("anchor_integrity_output.example.json")
    cycle = payload["checks"]["cycle_check"]
    cycle.update(
        {
            "status": "completed",
            "result": "low",
            "reason": None,
            "algorithm": "typed_scc_anchor_v0_1",
            "checked_relation_types": ["supported_by_claim"],
        }
    )
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_supported_claim_requires_completed_relation_verification() -> None:
    payload = example("anchor_integrity_output.example.json")
    result = payload["claim_results"][0]
    result["relation_verification_status"] = "not_run"
    result["relation_result"] = None
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_supported_claim_requires_verified_source_identity() -> None:
    payload = example("anchor_integrity_output.example.json")
    payload["claim_results"][0]["source_identity_status"] = "mismatch"
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_supported_claim_requires_verified_source_integrity() -> None:
    payload = example("anchor_integrity_output.example.json")
    payload["claim_results"][0]["source_integrity_status"] = "mismatch"
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_supported_claim_requires_resolved_locator() -> None:
    payload = example("anchor_integrity_output.example.json")
    payload["claim_results"][0]["locator_status"] = "unresolved"
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_supported_claim_requires_satisfied_subject_binding() -> None:
    payload = example("anchor_integrity_output.example.json")
    payload["claim_results"][0]["subject_binding_status"] = "unsatisfied"
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_supported_claim_rejects_detected_contradiction() -> None:
    payload = example("anchor_integrity_output.example.json")
    payload["claim_results"][0]["contradiction_status"] = "detected"
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_partial_claim_set_cannot_emit_whole_response_coverage() -> None:
    payload = example("anchor_integrity_output.example.json")
    payload["claim_set"]["materialization_status"] = "partial"
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_partial_claim_set_accepts_explicit_not_applicable_coverage() -> None:
    payload = example("anchor_integrity_output.example.json")
    payload["claim_set"]["materialization_status"] = "partial"
    for metric in payload["coverage"].values():
        metric.update(
            {
                "status": "not_applicable",
                "numerator": None,
                "denominator": None,
                "value": None,
                "reason": "claim_set_is_not_complete",
            }
        )
    assert_valid("anchor_integrity_output_v0_1.schema.json", payload)


def test_evidence_source_requires_stable_source_id() -> None:
    payload = example("evidence_packet.example.json")
    del payload["sources"][0]["source_id"]
    assert_invalid("anchor_integrity_evidence_packet_v0_1.schema.json", payload)


def test_evidence_item_requires_exact_locator() -> None:
    payload = example("evidence_packet.example.json")
    del payload["evidence_items"][0]["locator"]
    assert_invalid("anchor_integrity_evidence_packet_v0_1.schema.json", payload)


def test_non_completed_source_check_cannot_retain_verified_result() -> None:
    payload = example("evidence_packet.example.json")
    check = payload["sources"][0]["identity_verification"]
    check.update(
        {
            "status": "not_run",
            "result": "verified",
            "reason": "identity_check_not_run",
        }
    )
    assert_invalid("anchor_integrity_evidence_packet_v0_1.schema.json", payload)


def test_non_completed_relation_check_cannot_retain_result() -> None:
    payload = example("relation_verification_packet.example.json")
    relation = payload["relations"][0]
    relation["relation_verification"].update(
        {
            "status": "not_run",
            "result": "supported",
            "reason": "relation_check_not_run",
        }
    )
    relation["verifier_record_id"] = None
    assert_invalid(
        "anchor_integrity_relation_verification_packet_v0_1.schema.json",
        payload,
    )


def test_completed_relation_check_requires_non_null_result() -> None:
    payload = example("relation_verification_packet.example.json")
    payload["relations"][0]["relation_verification"]["result"] = None
    assert_invalid(
        "anchor_integrity_relation_verification_packet_v0_1.schema.json",
        payload,
    )


def test_completed_relation_check_requires_verifier_record() -> None:
    payload = example("relation_verification_packet.example.json")
    payload["relations"][0]["verifier_record_id"] = None
    assert_invalid(
        "anchor_integrity_relation_verification_packet_v0_1.schema.json",
        payload,
    )


def test_input_binding_requires_packet_digest() -> None:
    payload = example("anchor_integrity_input.example.json")
    del payload["packet_bindings"]["claim_packet"]["sha256"]
    assert_invalid("anchor_integrity_input_v0_1.schema.json", payload)


def test_claim_digest_must_be_sha256_hex() -> None:
    payload = example("claim_packet.example.json")
    payload["claim_set"]["claims"][0]["claim_digest"] = "not-a-digest"
    assert_invalid("anchor_integrity_claim_packet_v0_1.schema.json", payload)


def test_output_cannot_activate_release_authority() -> None:
    payload = example("anchor_integrity_output.example.json")
    payload["release_authority_activation"] = True
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_output_cannot_claim_authority_effect() -> None:
    payload = example("anchor_integrity_output.example.json")
    payload["authority_effect"] = "release"
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_response_recommendation_cannot_be_enforced() -> None:
    payload = example("anchor_integrity_output.example.json")
    payload["response_recommendation"]["enforced"] = True
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_not_implemented_boundary_is_fixed() -> None:
    payload = example("anchor_integrity_output.example.json")
    payload["not_implemented"].remove("production_response_enforcement")
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_unexpected_top_level_property_is_rejected() -> None:
    payload = example("anchor_integrity_output.example.json")
    payload["release_decision"] = "PASS"
    assert_invalid("anchor_integrity_output_v0_1.schema.json", payload)


def test_examples_do_not_mutate_during_validation() -> None:
    for schema_name, example_name in SCHEMA_EXAMPLE_PAIRS.items():
        payload = example(example_name)
        before = deepcopy(payload)
        assert_valid(schema_name, payload)
        assert payload == before


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
