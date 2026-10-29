from __future__ import annotations

from copy import deepcopy
import base64
import hashlib
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

# Fixed-example byte checks only. This is not a production binding validator.
# Decode historical source as data: never import/execute it or read current HEAD.
PINNED_SOURCE_COMMIT = "34431ec8ebe305a83273ffd39b78f083219f03e6"
PINNED_SOURCE_PATH = "scripts/anchor_integrity_adapter_v0.py"
PINNED_SOURCE_BLOB = "3f4afe26be361fddda153f72dd20803183a85a8e"
PINNED_SOURCE_SHA256 = (
    "3ceb60e9ca0a5d3a7d142bc91f5f51ca0376f54a37f33c3f359774f25c42f1d0"
)
SOURCE_SNAPSHOT = (
    ROOT / "tests" / "fixtures" / "anchor_integrity_v0_1"
    / "adapter_v0_34431ec8.source.json"
)
EXAMPLE_PREFIX = "examples/anchor_integrity_v0_1/"
PACKET_LINKS = (
    ("relation_verification_packet.example.json", ("claim_packet_binding",),
     "claim_packet.example.json"),
    ("relation_verification_packet.example.json", ("evidence_packet_binding",),
     "evidence_packet.example.json"),
    ("anchor_integrity_input.example.json", ("packet_bindings", "claim_packet"),
     "claim_packet.example.json"),
    ("anchor_integrity_input.example.json", ("packet_bindings", "evidence_packet"),
     "evidence_packet.example.json"),
    ("anchor_integrity_input.example.json",
     ("packet_bindings", "relation_verification_packet"),
     "relation_verification_packet.example.json"),
    ("anchor_integrity_output.example.json", ("input_sha256",),
     "anchor_integrity_input.example.json"),
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode_source_snapshot(snapshot: dict) -> bytes:
    assert snapshot["record_role"] == "historical_source_bytes_for_fixture_regression"
    assert snapshot["authority_effect"] == "none"
    assert snapshot["source_repository"] == "HKati/pulse-release-gates-0.1"
    assert snapshot["source_commit"] == PINNED_SOURCE_COMMIT
    assert snapshot["source_path"] == PINNED_SOURCE_PATH
    assert snapshot["git_blob_sha1"] == PINNED_SOURCE_BLOB
    assert snapshot["content_sha256"] == PINNED_SOURCE_SHA256
    assert snapshot["encoding"] == "base64"
    data = base64.b64decode(snapshot["content_base64"], validate=True)
    assert len(data) == snapshot["byte_length"] == 11457
    git_object = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    assert hashlib.sha1(git_object).hexdigest() == PINNED_SOURCE_BLOB
    assert _sha256_bytes(data) == PINNED_SOURCE_SHA256
    return data


def _source_bytes() -> bytes:
    return _decode_source_snapshot(load_json(SOURCE_SNAPSHOT))


def _line_range_bytes(data: bytes, start: int, end: int) -> bytes:
    """One-based inclusive LF-delimited lines, without byte normalization."""
    parts = data.split(b"\n")
    lines = [part + b"\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    if type(start) is not int or type(end) is not int:
        raise ValueError("line endpoints must be integers, not booleans")
    if not 1 <= start <= end <= len(lines):
        raise ValueError("line range is outside the preserved source")
    return b"".join(lines[start - 1:end])


def _assert_example_source_binding(evidence: dict, data: bytes) -> None:
    # Check the external pin before accepting even self-consistent packet hashes.
    assert _sha256_bytes(data) == PINNED_SOURCE_SHA256, "pinned source bytes"
    assert len(evidence["sources"]) == len(evidence["evidence_items"]) == 1
    source = evidence["sources"][0]
    item = evidence["evidence_items"][0]
    assert source["source_type"] == "repository_file"
    assert source["revision"] == PINNED_SOURCE_COMMIT
    assert source["canonical_identifier"] == (
        PINNED_SOURCE_PATH + "@" + PINNED_SOURCE_COMMIT
    )
    assert source["source_id"] == item["source_id"] == "source-0001"
    assert source["content_sha256"] == _sha256_bytes(data), "whole-source digest"
    assert item["locator"] == {
        "type": "line_range", "start_line": 100, "end_line": 142,
    }, "complete proxy function locator"
    selected = _line_range_bytes(
        data, item["locator"]["start_line"], item["locator"]["end_line"]
    )
    assert item["content_sha256"] == _sha256_bytes(selected), "selected-content digest"
    assert item["content_sha256"] != source["content_sha256"]


def _packet_bytes() -> dict[str, bytes]:
    return {
        name: (EXAMPLE_DIR / name).read_bytes()
        for name in SCHEMA_EXAMPLE_PAIRS.values()
    }


def _encode_example(payload: dict) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _assert_packet_link(packets: dict[str, bytes], link: tuple) -> None:
    consumer_name, keys, target_name = link
    value = json.loads(packets[consumer_name])
    for key in keys:
        value = value[key]
    if keys == ("input_sha256",):
        claimed = value
    else:
        assert value["path"] == EXAMPLE_PREFIX + target_name, "packet path"
        assert value["schema_version"] == json.loads(packets[target_name])["schema_version"]
        claimed = value["sha256"]
    assert claimed == _sha256_bytes(packets[target_name]), (
        f"packet digest: {consumer_name} -> {target_name}"
    )


def test_preserved_source_matches_baseline_git_blob_and_sha256() -> None:
    data = _source_bytes()
    inventory = load_json(BASELINE)
    assert inventory["source_commit"] == PINNED_SOURCE_COMMIT
    entry, = [
        row for row in inventory["v0_source_files"]
        if row["path"] == PINNED_SOURCE_PATH
    ]
    git_object = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    assert entry["git_blob_sha1"] == hashlib.sha1(git_object).hexdigest()


def test_verified_example_source_digest_matches_pinned_bytes() -> None:
    source = example("evidence_packet.example.json")["sources"][0]
    assert source["content_sha256"] == _sha256_bytes(_source_bytes())


def test_verified_example_excerpt_digest_matches_selected_bytes() -> None:
    evidence = example("evidence_packet.example.json")
    item = evidence["evidence_items"][0]
    selected = _line_range_bytes(
        _source_bytes(), item["locator"]["start_line"], item["locator"]["end_line"]
    )
    assert item["content_sha256"] == _sha256_bytes(selected)


def test_verified_example_locator_contains_the_complete_proxy_computation() -> None:
    evidence = example("evidence_packet.example.json")
    data = _source_bytes()
    _assert_example_source_binding(evidence, data)
    selected = _line_range_bytes(data, 100, 142)
    assert len(selected) == 1813
    assert selected.startswith(b"def _anchor_signals_from_status(")
    assert selected.endswith(b"    return anchor_presence, anchor_coverage, evidence\n")
    assert (
        b"anchor_coverage = sum(1 for v in present if v) / float(len(present))"
        in selected
    )


@pytest.mark.parametrize("link", PACKET_LINKS)
def test_example_packet_link_matches_exact_file_bytes(link: tuple) -> None:
    _assert_packet_link(_packet_bytes(), link)


@pytest.mark.parametrize("link", PACKET_LINKS)
def test_stale_packet_link_is_rejected(link: tuple) -> None:
    packets = _packet_bytes()
    consumer_name, keys, _ = link
    consumer = json.loads(packets[consumer_name])
    value = consumer
    for key in keys[:-1]:
        value = value[key]
    if keys == ("input_sha256",):
        value[keys[-1]] = "0" * 64
    else:
        value[keys[-1]]["sha256"] = "0" * 64
    packets[consumer_name] = _encode_example(consumer)
    with pytest.raises(AssertionError, match="packet digest"):
        _assert_packet_link(packets, link)


@pytest.mark.parametrize("name", (
    "claim_packet.example.json", "evidence_packet.example.json",
    "relation_verification_packet.example.json", "anchor_integrity_input.example.json",
))
def test_changed_packet_bytes_are_not_hidden_by_json_equivalence(name: str) -> None:
    packets = _packet_bytes()
    before = json.loads(packets[name])
    packets[name] += b" "
    assert json.loads(packets[name]) == before
    with pytest.raises(AssertionError, match="packet digest"):
        for link in PACKET_LINKS:
            _assert_packet_link(packets, link)


def test_whole_source_digest_cannot_substitute_for_excerpt_digest() -> None:
    evidence = example("evidence_packet.example.json")
    evidence["evidence_items"][0]["content_sha256"] = (
        evidence["sources"][0]["content_sha256"]
    )
    with pytest.raises(AssertionError, match="selected-content digest"):
        _assert_example_source_binding(evidence, _source_bytes())


def test_original_incorrect_digest_is_rejected_after_outer_packets_are_rehashed() -> None:
    packets = _packet_bytes()
    evidence = json.loads(packets["evidence_packet.example.json"])
    wrong_digest = "e2b22d0806d790f0a27387e6dd5d25f84d8fd7acca04ee23d027978b6350d6d9"
    evidence["sources"][0]["content_sha256"] = wrong_digest
    evidence["evidence_items"][0]["content_sha256"] = wrong_digest
    assert_valid("anchor_integrity_evidence_packet_v0_1.schema.json", evidence)
    packets["evidence_packet.example.json"] = _encode_example(evidence)
    # Topological order: evidence -> relation -> input -> output.
    for link in PACKET_LINKS:
        consumer_name, keys, target_name = link
        consumer = json.loads(packets[consumer_name])
        value = consumer
        for key in keys[:-1]:
            value = value[key]
        if keys == ("input_sha256",):
            value[keys[-1]] = _sha256_bytes(packets[target_name])
        else:
            value[keys[-1]]["sha256"] = _sha256_bytes(packets[target_name])
        packets[consumer_name] = _encode_example(consumer)
    for link in PACKET_LINKS:
        _assert_packet_link(packets, link)
    with pytest.raises(AssertionError, match="whole-source digest"):
        _assert_example_source_binding(evidence, _source_bytes())


@pytest.mark.parametrize("location", ("before_excerpt", "inside_excerpt", "end_of_file"))
def test_source_byte_changes_cannot_be_accepted_by_rehashing_evidence(location: str) -> None:
    data = _source_bytes()
    if location == "before_excerpt":
        changed = b"!" + data[1:]
    elif location == "inside_excerpt":
        changed = data.replace(b'q4_slo_ok', b'q4_bad_ok', 1)
    else:
        changed = data + b"\n"
    assert changed != data
    evidence = example("evidence_packet.example.json")
    evidence["sources"][0]["content_sha256"] = _sha256_bytes(changed)
    evidence["evidence_items"][0]["content_sha256"] = _sha256_bytes(
        _line_range_bytes(changed, 100, 142)
    )
    with pytest.raises(AssertionError, match="pinned source bytes"):
        _assert_example_source_binding(evidence, changed)


@pytest.mark.parametrize(("start", "end"), (
    (0, 142), (-1, 142), (142, 100), (100, 1000000),
    (True, 142), (100, False), ("100", 142), (100, 142.0),
))
def test_invalid_source_line_ranges_are_rejected(start: object, end: object) -> None:
    with pytest.raises(ValueError):
        _line_range_bytes(_source_bytes(), start, end)


def test_line_selection_preserves_terminators_and_an_unterminated_final_line() -> None:
    data = b"one\r\ntwo\nthree"
    assert _line_range_bytes(data, 1, 2) == b"one\r\ntwo\n"
    assert _line_range_bytes(data, 2, 3) == b"two\nthree"
    assert _line_range_bytes(data, 3, 3) == b"three"


def test_historical_source_snapshot_corruption_fails_closed() -> None:
    snapshot = load_json(SOURCE_SNAPSHOT)
    data = _source_bytes()
    changed = b"!" + data[1:]
    snapshot["content_base64"] = base64.b64encode(changed).decode("ascii")
    with pytest.raises(AssertionError):
        _decode_source_snapshot(snapshot)


def test_historical_source_snapshot_rejects_invalid_base64() -> None:
    snapshot = load_json(SOURCE_SNAPSHOT)
    snapshot["content_base64"] = "!not-base64!"
    with pytest.raises(ValueError):
        _decode_source_snapshot(snapshot)


def test_historical_source_snapshot_missing_bytes_fail_closed() -> None:
    snapshot = load_json(SOURCE_SNAPSHOT)
    del snapshot["content_base64"]
    with pytest.raises(KeyError):
        _decode_source_snapshot(snapshot)


def test_source_binding_rejects_a_different_revision() -> None:
    evidence = example("evidence_packet.example.json")
    evidence["sources"][0]["revision"] = "0" * 40
    with pytest.raises(AssertionError):
        _assert_example_source_binding(evidence, _source_bytes())


def test_source_binding_rejects_a_different_canonical_identifier() -> None:
    evidence = example("evidence_packet.example.json")
    evidence["sources"][0]["canonical_identifier"] = "other.py@" + PINNED_SOURCE_COMMIT
    with pytest.raises(AssertionError):
        _assert_example_source_binding(evidence, _source_bytes())


def test_original_short_locator_is_rejected_even_with_its_correct_excerpt_digest() -> None:
    evidence = example("evidence_packet.example.json")
    item = evidence["evidence_items"][0]
    item["locator"] = {"type": "line_range", "start_line": 89, "end_line": 126}
    item["content_sha256"] = _sha256_bytes(_line_range_bytes(_source_bytes(), 89, 126))
    with pytest.raises(AssertionError, match="complete proxy function locator"):
        _assert_example_source_binding(evidence, _source_bytes())


def test_source_snapshot_is_not_a_normative_or_executable_adapter() -> None:
    snapshot = load_json(SOURCE_SNAPSHOT)
    assert snapshot["authority_effect"] == "none"
    assert SOURCE_SNAPSHOT.suffix == ".json"
    assert "historical_source_bytes" in snapshot["record_role"]
    # The actual v0 source is not needed or executed by the fixture regression.
    assert SOURCE_SNAPSHOT.as_posix().endswith(
        "tests/fixtures/anchor_integrity_v0_1/adapter_v0_34431ec8.source.json"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
