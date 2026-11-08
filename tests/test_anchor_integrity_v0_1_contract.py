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


# WP2A executable local-binding tests. The preceding WP1 functions are retained.
import contextlib as _wp2_contextlib
import importlib.util as _wp2_importlib
import io as _wp2_io
import os as _wp2_os
import shutil as _wp2_shutil
import subprocess as _wp2_subprocess
import sys as _wp2_sys
from functools import lru_cache as _wp2_lru_cache

WP2_DEMO = EXAMPLE_DIR / "wp2a_local_binding"
WP2_TOOL = ROOT / "tools" / "check_anchor_integrity_bindings_v0_1.py"
WP2_INPUT_PIN = "be4865f6544ce1cc91b5af5dab89357b71fe4629a92ecc079de99f8e95af9d74"
WP2_CARRIERS_PIN = "4ad4b7301042f2b136cd13cc18f01f7b2d0b7ca823a3e46032e2f3d7e9c4e4b2"


@_wp2_lru_cache(maxsize=1)
def _wp2_module():
    spec = _wp2_importlib.spec_from_file_location("anchor_wp2a_checker", WP2_TOOL)
    module = _wp2_importlib.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _wp2_write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _wp2_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wp2_fixture(tmp_path):
    dest = tmp_path / "bundle"
    _wp2_shutil.copytree(WP2_DEMO, dest)
    return dest


def _wp2_rebind(root):
    """Explicitly approve changed *test* roots, not an authentication operation."""
    inp = load_json(root / "input.json")
    rp = load_json(root / "relations.json")
    for role, filename, rpkey in (("claim_packet", "claims.json", "claim_packet_binding"),
                                  ("evidence_packet", "evidence.json", "evidence_packet_binding")):
        inp["packet_bindings"][role]["sha256"] = _wp2_hash(root / filename)
        rp[rpkey] = deepcopy(inp["packet_bindings"][role])
    _wp2_write(root / "relations.json", rp)
    inp["packet_bindings"]["relation_verification_packet"]["sha256"] = _wp2_hash(root / "relations.json")
    inp["legacy_overlay"]["sha256"] = _wp2_hash(root / "legacy.json")
    _wp2_write(root / "input.json", inp)
    carrier = load_json(root / "carriers.json")
    carrier["input_sha256"] = _wp2_hash(root / "input.json")
    _wp2_write(root / "carriers.json", carrier)
    return _wp2_hash(root / "input.json"), _wp2_hash(root / "carriers.json")


def _wp2_run(root, pins=None, **kw):
    first, second = pins or (WP2_INPUT_PIN, WP2_CARRIERS_PIN)
    return _wp2_module().verify_bundle(root, kw.get("input_path", "input.json"), first,
                                     kw.get("carriers_path", "carriers.json"), second)


def _wp2_issue(report, code):
    return any(x["code"] == code for x in report["issues"])


def _wp2_assert_limits(report):
    assert report["authority_effect"] == "none"
    assert report["release_authority_activation"] is False
    assert report["requested_checks_complete"] is False
    for check in report["unperformed_checks"].values():
        assert check["status"] == "not_run" and check["result"] is None
    for check in report["checks"]:
        if check["status"] != "completed":
            assert check["result"] is None and check["reason"]
    for relation in report["recorded_relation_results"]:
        assert relation["accepted_as_semantic_support"] is False
    _wp2_module().SchemaSet().validate("report", report)


def test_wp2a_complete_local_demo_and_stable_pins():
    assert _wp2_hash(WP2_DEMO / "input.json") == WP2_INPUT_PIN
    assert _wp2_hash(WP2_DEMO / "carriers.json") == WP2_CARRIERS_PIN
    report = _wp2_run(WP2_DEMO)
    assert report["status"] == "LOCAL_BINDINGS_CONSISTENT"
    assert report["issues"] == []
    assert report["counts"] == {"claims": 2, "sources": 1, "evidence_items": 1,
        "relations": 1, "claims_with_recorded_anchors": 1, "claims_without_recorded_anchors": 1}
    _wp2_assert_limits(report)


@pytest.mark.parametrize("role", ("claims", "evidence", "relations", "input", "carriers"))
def test_wp2a_demo_packets_conform_to_unchanged_or_explicit_new_schema(role):
    _wp2_module().SchemaSet().validate(role, load_json(WP2_DEMO / (role + ".json")))


@pytest.mark.parametrize("filename", ("input.json", "carriers.json", "claims.json", "evidence.json", "relations.json", "legacy.json", "source.txt", "response.txt"))
def test_wp2a_missing_carriers_remain_incomplete(tmp_path, filename):
    root = _wp2_fixture(tmp_path)
    (root / filename).unlink()
    report = _wp2_run(root)
    assert report["status"] == "LOCAL_BINDINGS_INCOMPLETE"
    assert _wp2_issue(report, "missing_carrier")
    _wp2_assert_limits(report)


@pytest.mark.parametrize("filename", ("input.json", "carriers.json", "claims.json", "evidence.json", "relations.json", "legacy.json", "source.txt", "response.txt"))
def test_wp2a_changed_bytes_are_invalid_under_fixed_expectations(tmp_path, filename):
    root = _wp2_fixture(tmp_path)
    p = root / filename
    p.write_bytes(p.read_bytes() + b"\n")
    report = _wp2_run(root)
    assert report["status"] == "LOCAL_BINDINGS_INVALID"
    _wp2_assert_limits(report)


@pytest.mark.parametrize("value", ("", "0" * 63, "0" * 65, "A" * 64, "z" * 64, "0" * 64, None, True))
@pytest.mark.parametrize("which", (0, 1))
def test_wp2a_expected_roots_are_required_and_not_inferred(tmp_path, value, which):
    pins = [WP2_INPUT_PIN, WP2_CARRIERS_PIN]
    pins[which] = value
    report = _wp2_run(_wp2_fixture(tmp_path), pins)
    assert report["status"] == "LOCAL_BINDINGS_INVALID"
    _wp2_assert_limits(report)


@pytest.mark.parametrize("data", (b'{"x":1,"x":2}', b'{"x":{"a":1,"a":2}}', b'NaN', b'Infinity', b'-Infinity', b'1e9999', b'"\\ud800"', b'\xef\xbb\xbf{}', b'\xff', b'{bad}', b'{"x":1} trailing'))
def test_wp2a_strict_json_rejects_ambiguous_or_invalid_values(data):
    with pytest.raises(_wp2_module().BindingError):
        _wp2_module().strict_json(data)


@pytest.mark.parametrize("data,expected", ((b'{}', {}), (b'{"x":null}', {"x": None}), ('{"word":"árvíz"}'.encode(), {"word":"árvíz"}), (b'[true,1,1.5]', [True,1,1.5])))
def test_wp2a_strict_json_accepts_regular_json(data, expected):
    assert _wp2_module().strict_json(data) == expected


@pytest.mark.parametrize("case", ("depth", "nodes", "items", "bytes"))
def test_wp2a_json_resource_bounds(case, monkeypatch):
    m = _wp2_module()
    if case == "depth":
        monkeypatch.setattr(m, "MAX_DEPTH", 3); data = b'[[[[0]]]]'
    elif case == "nodes":
        monkeypatch.setattr(m, "MAX_NODES", 2); data = b'[0,1,2]'
    elif case == "items":
        monkeypatch.setattr(m, "MAX_ITEMS", 2); data = b'[0,1,2]'
    else:
        monkeypatch.setattr(m, "MAX_FILE_BYTES", 2); data = b'[0]'
    with pytest.raises(m.BindingError):
        m.strict_json(data)


@pytest.mark.parametrize("start,end", ((0,1),(-1,1),(2,1),(1,4),(True,1),(1,False),(1.0,2),(1,2.0),("1",2),(1,None)))
def test_wp2a_invalid_line_bounds(start, end):
    with pytest.raises(_wp2_module().BindingError):
        _wp2_module().select_content(b"one\r\ntwo\nthree", {"type":"line_range","start_line":start,"end_line":end})


@pytest.mark.parametrize("data,start,end,expected", ((b'a\r\nb\nc',1,2,b'a\r\nb\n'),(b'a\nb',2,2,b'b'),(b'a\n',1,1,b'a\n'),(b'\n',1,1,b'\n'),(b'a\rb',1,1,b'a\rb')))
def test_wp2a_line_selection_is_exact_bytes(data,start,end,expected):
    assert _wp2_module().select_content(data,{"type":"line_range","start_line":start,"end_line":end}) == expected


@pytest.mark.parametrize("data,start,end", ((b'',1,1),(b'a\n',2,2)))
def test_wp2a_no_phantom_line_after_final_lf(data,start,end):
    with pytest.raises(_wp2_module().BindingError):
        _wp2_module().select_content(data,{"type":"line_range","start_line":start,"end_line":end})


@pytest.mark.parametrize("start,end", ((-1,1),(0,0),(2,1),(0,99),(True,1),(0,False),(0.0,1),(0,1.0),("0",1),(0,None)))
def test_wp2a_invalid_character_bounds(start,end):
    with pytest.raises(_wp2_module().BindingError):
        _wp2_module().select_content(b'abc',{'type':'character_span','start':start,'end':end})


@pytest.mark.parametrize("text,start,end,expected", (('árvíz',0,2,'ár'),('A😀B',1,2,'😀'),('e\u0301',0,1,'e'),('e\u0301',0,2,'e\u0301'),('x\r\ny',1,3,'\r\n')))
def test_wp2a_unicode_offsets_do_not_normalize(text,start,end,expected):
    assert _wp2_module().select_content(text.encode(),{'type':'character_span','start':start,'end':end}) == expected.encode()


def test_wp2a_character_span_requires_utf8():
    with pytest.raises(_wp2_module().BindingError,match='character_source_not_utf8'):
        _wp2_module().select_content(b'\xff',{'type':'character_span','start':0,'end':1})


@pytest.mark.parametrize("where", ("claim", "evidence"))
def test_wp2a_json_pointer_is_explicitly_unimplemented(tmp_path, where):
    root = _wp2_fixture(tmp_path)
    p = root / ('claims.json' if where == 'claim' else 'evidence.json')
    doc = load_json(p)
    item = doc['claim_set']['claims'][0] if where == 'claim' else doc['evidence_items'][0]
    item['locator'] = {'type':'json_pointer','value':'/text'}
    _wp2_write(p,doc)
    report = _wp2_run(root,_wp2_rebind(root))
    assert report['status'] == 'LOCAL_BINDINGS_INCOMPLETE'
    assert _wp2_issue(report,'json_pointer_projection_not_implemented')
    _wp2_assert_limits(report)


@pytest.mark.parametrize("path", ('../outside','/absolute','a/../../b','a\\b','C:/file','https://host/a','a//b','a/./b','./a','.','..','a/','a\n','a\x00','a.','a/%2e%2e/b','a b'))
def test_wp2a_unsafe_relative_paths_are_rejected(path):
    with pytest.raises(_wp2_module().BindingError):
        _wp2_module().safe_relative(path)


@pytest.mark.parametrize("where", ('input','packet','source','response','legacy'))
def test_wp2a_no_path_escape_in_any_read_role(tmp_path,where):
    root = _wp2_fixture(tmp_path)
    if where == 'input':
        report = _wp2_run(root,input_path='../outside')
    else:
        name = 'carriers.json' if where in ('source','response') else 'input.json'
        p=root/name; doc=load_json(p)
        if where=='packet':doc['packet_bindings']['claim_packet']['path']='../outside'
        elif where=='legacy':doc['legacy_overlay']['path']='../outside'
        elif where=='source':doc['sources'][0]['path']='../outside'
        else:doc['source_response']['path']='../outside'
        _wp2_write(p,doc)
        report=_wp2_run(root,_wp2_rebind(root))
    assert report['status']=='LOCAL_BINDINGS_INVALID'
    assert _wp2_issue(report,'unsafe_relative_path')


@pytest.mark.parametrize("kind", ('file_symlink','directory_symlink','hardlink','fifo'))
def test_wp2a_link_and_special_file_carriers_are_rejected(tmp_path,kind):
    root=_wp2_fixture(tmp_path); target=root/'source.txt'; data=target.read_bytes();target.unlink()
    if kind=='file_symlink':
        outside=tmp_path/'outside';outside.write_bytes(data);target.symlink_to(outside)
    elif kind=='hardlink':
        outside=tmp_path/'outside';outside.write_bytes(data);_wp2_os.link(outside,target)
    elif kind=='fifo':
        _wp2_os.mkfifo(target)
    else:
        outside=tmp_path/'other';outside.mkdir();(outside/'source.txt').write_bytes(data)
        (root/'linked').symlink_to(outside,target_is_directory=True)
        carrier=load_json(root/'carriers.json');carrier['sources'][0]['path']='linked/source.txt';_wp2_write(root/'carriers.json',carrier)
    report=_wp2_run(root,_wp2_rebind(root))
    assert report['status']=='LOCAL_BINDINGS_INVALID'


@pytest.mark.parametrize("kind", ('duplicate_claim_id','duplicate_source_id','duplicate_evidence_id','duplicate_binding_id','duplicate_map_id'))
def test_wp2a_unique_ids_are_required_beyond_unique_json_objects(tmp_path,kind):
    root=_wp2_fixture(tmp_path)
    filename={'duplicate_claim_id':'claims.json','duplicate_source_id':'evidence.json','duplicate_evidence_id':'evidence.json','duplicate_binding_id':'relations.json','duplicate_map_id':'carriers.json'}[kind]
    p=root/filename;d=load_json(p)
    if kind=='duplicate_claim_id':
        d['claim_set']['claims'][1]['claim_id']=d['claim_set']['claims'][0]['claim_id']
    else:
        key={'duplicate_source_id':'sources','duplicate_evidence_id':'evidence_items','duplicate_binding_id':'relations','duplicate_map_id':'sources'}[kind]
        item=deepcopy(d[key][0])
        if kind in ('duplicate_source_id','duplicate_map_id'):item['canonical_identifier']='different'
        elif kind=='duplicate_evidence_id':item['content_sha256']='0'*64
        else:item['relation_type']='contextualizes'
        d[key].append(item)
    _wp2_write(p,d);report=_wp2_run(root,_wp2_rebind(root))
    assert report['status']=='LOCAL_BINDINGS_INVALID'
    assert any(x['code'].startswith('duplicate_') for x in report['issues'])


@pytest.mark.parametrize("case", ('claim_subject','evidence_subject','relation_subject','response_id','source_name','source_revision','source_reference','claim_reference','evidence_reference','expected_subject','expected_run','observed_subject','observed_run','claim_digest','claim_span','selected_digest','packet_id'))
def test_wp2a_rehashed_outer_packets_do_not_hide_inner_binding_errors(tmp_path,case):
    root=_wp2_fixture(tmp_path)
    filename = ('claims.json' if case in ('claim_subject','claim_digest','claim_span','packet_id') else
                'relations.json' if case in ('relation_subject','claim_reference','evidence_reference') else
                'carriers.json' if case in ('response_id','source_name','source_revision') else 'evidence.json')
    p=root/filename;d=load_json(p)
    if case.endswith('_subject') and case in ('claim_subject','evidence_subject','relation_subject'):d['subject']['subject_id']='other'
    elif case=='response_id':d['source_response']['source_response_id']='other'
    elif case=='source_name':d['sources'][0]['canonical_identifier']='other'
    elif case=='source_revision':d['sources'][0]['revision']='other'
    elif case=='source_reference':d['evidence_items'][0]['source_id']='other'
    elif case=='claim_reference':d['relations'][0]['claim_id']='other'
    elif case=='evidence_reference':d['relations'][0]['evidence_id']='other'
    elif case in ('expected_subject','observed_subject'):d['evidence_items'][0]['subject_binding'][case+'_id']='other'
    elif case in ('expected_run','observed_run'):d['evidence_items'][0]['subject_binding'][case+'_id']='other'
    elif case=='claim_digest':d['claim_set']['claims'][0]['claim_digest']='0'*64
    elif case=='claim_span':d['claim_set']['claims'][0]['locator']['end']-=1
    elif case=='selected_digest':d['evidence_items'][0]['content_sha256']='0'*64
    else:d['packet_id']='wp2a-evidence'
    _wp2_write(p,d);report=_wp2_run(root,_wp2_rebind(root))
    assert report['status']=='LOCAL_BINDINGS_INVALID'
    _wp2_assert_limits(report)


@pytest.mark.parametrize("case", ('response_map','source_map','observed_subject','observed_run','partial_claim_set','invalid_claim_set'))
def test_wp2a_missing_recorded_measurements_do_not_become_success(tmp_path,case):
    root=_wp2_fixture(tmp_path)
    filename='carriers.json' if case.endswith('_map') else 'claims.json' if case.endswith('claim_set') else 'evidence.json'
    p=root/filename;d=load_json(p)
    if case=='response_map':d['source_response']=None
    elif case=='source_map':d['sources']=[]
    elif case in ('observed_subject','observed_run'):d['evidence_items'][0]['subject_binding'][case+'_id']=None
    else:d['claim_set']['materialization_status']='partial' if case.startswith('partial') else 'invalid'
    _wp2_write(p,d);report=_wp2_run(root,_wp2_rebind(root))
    assert report['status']=='LOCAL_BINDINGS_INCOMPLETE'
    _wp2_assert_limits(report)


@pytest.mark.parametrize("declared", ('supported','contradicted','insufficient','unresolved'))
def test_wp2a_recorded_verifier_labels_are_not_semantic_verification(tmp_path,declared):
    root=_wp2_fixture(tmp_path);p=root/'relations.json';d=load_json(p)
    r=d['relations'][0];r['relation_verification']={'status':'completed','result':declared,'reason':None};r['verifier_record_id']='unsigned-record';r['relation_type']='supports'
    _wp2_write(p,d);report=_wp2_run(root,_wp2_rebind(root))
    assert report['status']=='LOCAL_BINDINGS_CONSISTENT'
    assert report['recorded_relation_results'][0]['declared_result']==declared
    _wp2_assert_limits(report)


def test_wp2a_fixed_root_rejects_consistently_rehashed_substitution(tmp_path):
    root=_wp2_fixture(tmp_path);p=root/'claims.json';d=load_json(p)
    d['claim_set']['claims'][0]['qualifiers'].append('substituted');_wp2_write(p,d)
    _wp2_rebind(root)
    assert _wp2_run(root)['status']=='LOCAL_BINDINGS_INVALID'
    # Different explicitly supplied roots admit a different local object, not its truth.
    report=_wp2_run(root,(_wp2_hash(root/'input.json'),_wp2_hash(root/'carriers.json')))
    assert report['status']=='LOCAL_BINDINGS_CONSISTENT';_wp2_assert_limits(report)


def test_wp2a_no_anchor_and_repeated_relations_do_not_inflate_claim_counts(tmp_path):
    root=_wp2_fixture(tmp_path);p=root/'relations.json';d=load_json(p)
    duplicate=deepcopy(d['relations'][0]);duplicate['binding_id']='binding-2';d['relations'].append(duplicate);_wp2_write(p,d)
    report=_wp2_run(root,_wp2_rebind(root));assert report['counts']['claims_with_recorded_anchors']==1
    d['relations']=[];_wp2_write(p,d);report=_wp2_run(root,_wp2_rebind(root))
    assert report['status']=='LOCAL_BINDINGS_CONSISTENT'
    assert report['counts']['claims_without_recorded_anchors']==2
    _wp2_assert_limits(report)


def test_wp2a_relation_cross_packet_hash_is_checked_separately(tmp_path):
    root=_wp2_fixture(tmp_path);p=root/'relations.json';d=load_json(p)
    d['claim_packet_binding']['sha256']='0'*64;_wp2_write(p,d)
    inp=load_json(root/'input.json');inp['packet_bindings']['relation_verification_packet']['sha256']=_wp2_hash(p);_wp2_write(root/'input.json',inp)
    carrier=load_json(root/'carriers.json');carrier['input_sha256']=_wp2_hash(root/'input.json');_wp2_write(root/'carriers.json',carrier)
    report=_wp2_run(root,(_wp2_hash(root/'input.json'),_wp2_hash(root/'carriers.json')))
    assert report['status']=='LOCAL_BINDINGS_INVALID'


def test_wp2a_carrier_manifest_must_bind_exact_input(tmp_path):
    root=_wp2_fixture(tmp_path);p=root/'carriers.json';d=load_json(p);d['input_sha256']='0'*64;_wp2_write(p,d)
    assert _wp2_run(root,(WP2_INPUT_PIN,_wp2_hash(p)))['status']=='LOCAL_BINDINGS_INVALID'


@pytest.mark.parametrize("name", ('input.json','carriers.json','claims.json','evidence.json','relations.json'))
def test_wp2a_unexpected_fields_cannot_bypass_packet_schema(tmp_path,name):
    root=_wp2_fixture(tmp_path);p=root/name;d=load_json(p);d['unknown']='forbidden';_wp2_write(p,d)
    report=_wp2_run(root,_wp2_rebind(root));assert report['status']=='LOCAL_BINDINGS_INVALID'


def test_wp2a_legacy_and_graph_are_byte_bound_not_semantically_accepted(tmp_path):
    root=_wp2_fixture(tmp_path);_wp2_write(root/'graph.json',{'schema':'fixture_graph_v0','edges':['uninterpreted']})
    inp=load_json(root/'input.json');inp['paradox_graph_binding']={'path':'graph.json','schema_version':'fixture_graph_v0','sha256':_wp2_hash(root/'graph.json')};_wp2_write(root/'input.json',inp)
    report=_wp2_run(root,_wp2_rebind(root));assert report['status']=='LOCAL_BINDINGS_CONSISTENT';_wp2_assert_limits(report)
    (root/'graph.json').write_bytes(b'{}');assert _wp2_run(root,(_wp2_hash(root/'input.json'),_wp2_hash(root/'carriers.json')))['status']=='LOCAL_BINDINGS_INVALID'


def test_wp2a_no_network_schema_resolution():
    for keyword in ('$ref','$dynamicRef','$recursiveRef'):
        with pytest.raises(_wp2_module().BindingError,match='schema_reference_not_allowed'):
            _wp2_module()._assert_self_contained({'properties':{'x':{keyword:'https://invalid/schema'}}})


def test_wp2a_report_deterministic_and_bundle_bytes_unchanged(tmp_path):
    root=_wp2_fixture(tmp_path);before={p.name:p.read_bytes() for p in root.iterdir()}
    a=_wp2_run(root);b=_wp2_run(root)
    assert a==b==_wp2_run(WP2_DEMO)
    assert before=={p.name:p.read_bytes() for p in root.iterdir()}


@pytest.mark.parametrize("case,exit_code", (('positive',0),('missing',2),('changed',1)))
def test_wp2a_real_cli_exit_and_report_contract(tmp_path,case,exit_code):
    root=_wp2_fixture(tmp_path)
    if case=='missing':(root/'source.txt').unlink()
    if case=='changed':(root/'source.txt').write_bytes(b'changed')
    result=_wp2_subprocess.run([_wp2_sys.executable,str(WP2_TOOL),'--bundle-root',str(root),'--input','input.json','--expected-input-sha256',WP2_INPUT_PIN,'--carriers','carriers.json','--expected-carriers-sha256',WP2_CARRIERS_PIN],capture_output=True,text=True,timeout=30)
    assert result.returncode==exit_code,result.stderr
    report=json.loads(result.stdout);_wp2_assert_limits(report)
    assert report==_wp2_run(root)


def test_wp2a_cli_requires_caller_digest_expectations(tmp_path):
    result=_wp2_subprocess.run([_wp2_sys.executable,str(WP2_TOOL),'--bundle-root',str(WP2_DEMO),'--input','input.json','--carriers','carriers.json'],capture_output=True,text=True,timeout=30)
    assert result.returncode==2 and not result.stdout


def test_wp2a_neither_new_manifest_registration_nor_gate_wiring_is_required():
    for path in ('ci/tools-tests.list','ci/pytest-tests.list'):
        assert _manifest_entries(ROOT/path).count(TEST_PATH)==1
    source=WP2_TOOL.read_text(encoding='utf-8')
    for unwanted in ('subprocess','urllib','requests','socket','eval(', 'exec(', 'os.system', 'check_gates.py'):
        assert unwanted not in source


@pytest.mark.parametrize("key", ('release_authority_activation','requested_checks_complete'))
def test_wp2a_output_schema_rejects_authority_or_unperformed_check_promotion(key):
    report=_wp2_run(WP2_DEMO);report[key]=True
    with pytest.raises(_wp2_module().BindingError):
        _wp2_module().SchemaSet().validate('report',report)

@pytest.mark.parametrize('where',('source','response'))
def test_wp2a_whole_source_hash_detects_changes_outside_selected_excerpt(tmp_path,where):
    root=_wp2_fixture(tmp_path)
    p=root/('source.txt' if where=='source' else 'response.txt')
    p.write_bytes(p.read_bytes()+b'\nUnselected changed tail')
    report=_wp2_run(root)
    assert report['status']=='LOCAL_BINDINGS_INVALID'
    key='source:source-1.sha256' if where=='source' else 'source_response.sha256'
    assert any(x['id']==key and x['result']=='mismatch' for x in report['checks'])


@pytest.mark.parametrize('case',('unknown_source','path_reuse','case_collision','legacy_tag'))
def test_wp2a_carrier_closure_and_opaque_tags(tmp_path,case):
    root=_wp2_fixture(tmp_path)
    if case=='legacy_tag':
        d=load_json(root/'legacy.json');d['schema']='wrong';_wp2_write(root/'legacy.json',d)
    else:
        d=load_json(root/'carriers.json')
        if case=='unknown_source':
            extra=deepcopy(d['sources'][0]);extra['source_id']='unknown';extra['path']='unknown.txt';d['sources'].append(extra)
        elif case=='path_reuse':d['sources'][0]['path']='response.txt'
        else:d['sources'][0]['path']='Response.txt';(root/'Response.txt').write_bytes((root/'source.txt').read_bytes())
        _wp2_write(root/'carriers.json',d)
    assert _wp2_run(root,_wp2_rebind(root))['status']=='LOCAL_BINDINGS_INVALID'


def test_wp2a_both_null_run_ids_do_not_create_a_run_verification(tmp_path):
    root=_wp2_fixture(tmp_path)
    for file in ('input.json','claims.json','evidence.json','relations.json'):
        d=load_json(root/file);d['subject']['run_id']=None
        if file=='evidence.json':
            d['evidence_items'][0]['subject_binding']['expected_run_id']=None
            d['evidence_items'][0]['subject_binding']['observed_run_id']=None
        _wp2_write(root/file,d)
    report=_wp2_run(root,_wp2_rebind(root))
    assert report['status']=='LOCAL_BINDINGS_CONSISTENT'
    match=[x for x in report['checks'] if x['id']=='evidence:evidence-1.recorded_run_id']
    assert len(match)==1 and match[0]['status']=='not_run' and match[0]['result'] is None
    _wp2_assert_limits(report)


def test_wp2a_verified_labels_cannot_promote_source_authentication(tmp_path):
    root=_wp2_fixture(tmp_path);p=root/'evidence.json';d=load_json(p)
    for key in ('identity_verification','integrity_verification'):
        d['sources'][0][key]={'status':'completed','result':'verified','reason':None}
    d['evidence_items'][0]['locator_verification']={'status':'completed','result':'resolved','reason':None}
    d['evidence_items'][0]['subject_binding']['verification']={'status':'completed','result':'satisfied','reason':None}
    _wp2_write(p,d);report=_wp2_run(root,_wp2_rebind(root))
    assert report['status']=='LOCAL_BINDINGS_CONSISTENT'
    _wp2_assert_limits(report)


def test_wp2a_wrong_root_report_preserves_expected_and_observed_hash(tmp_path):
    root=_wp2_fixture(tmp_path);p=root/'input.json';p.write_bytes(p.read_bytes()+b'\n')
    report=_wp2_run(root)
    assert report['expected_input_sha256']==WP2_INPUT_PIN
    assert report['input_sha256']==_wp2_hash(p)!=WP2_INPUT_PIN
    assert report['status']=='LOCAL_BINDINGS_INVALID'


def test_wp2a_original_wp1_examples_are_not_relabelled_as_complete_runtime_inputs(tmp_path):
    root=tmp_path/'legacy';dest=root/'examples/anchor_integrity_v0_1';dest.mkdir(parents=True)
    for name in SCHEMA_EXAMPLE_PAIRS.values():
        (dest/name).write_bytes((EXAMPLE_DIR/name).read_bytes())
    inp=load_json(dest/'anchor_integrity_input.example.json')
    carrier={'schema_version':'anchor_integrity_local_carriers_v0_1','candidate_status':'diagnostic_only','authority_effect':'none','input_sha256':_wp2_hash(dest/'anchor_integrity_input.example.json'),'source_response':None,'sources':[]}
    _wp2_write(root/'carriers.json',carrier)
    report=_wp2_module().verify_bundle(root,'examples/anchor_integrity_v0_1/anchor_integrity_input.example.json',carrier['input_sha256'],'carriers.json',_wp2_hash(root/'carriers.json'))
    assert report['status']=='LOCAL_BINDINGS_INCOMPLETE'
    assert _wp2_issue(report,'missing_carrier')
    assert _wp2_issue(report,'source_response_not_supplied')
    _wp2_assert_limits(report)


@pytest.mark.parametrize('case',('file','total'))
def test_wp2a_bounded_file_reads(case,tmp_path,monkeypatch):
    m=_wp2_module();(tmp_path/'one').write_bytes(b'1234');(tmp_path/'two').write_bytes(b'5678')
    with m.BundleReader(tmp_path) as reader:
        if case=='file':
            monkeypatch.setattr(m,'MAX_FILE_BYTES',3)
            with pytest.raises(m.BindingError,match='file_limit_exceeded'):reader.read('one','one')
        else:
            monkeypatch.setattr(m,'MAX_TOTAL_BYTES',7);reader.read('one','one')
            with pytest.raises(m.BindingError,match='bundle_limit_exceeded'):reader.read('two','two')


def test_wp2a_reader_refuses_metadata_change_during_read(tmp_path,monkeypatch):
    import types
    m=_wp2_module();(tmp_path/'one').write_bytes(b'1234');original=m.os.fstat;calls=[]
    def changed(fd):
        s=original(fd);calls.append(fd)
        if len(calls)==2:
            return types.SimpleNamespace(**{key:getattr(s,key)+(1 if key=='st_mtime_ns' else 0) for key in ('st_mode','st_nlink','st_size','st_dev','st_ino','st_mtime_ns','st_ctime_ns')})
        return s
    with m.BundleReader(tmp_path) as reader:
        monkeypatch.setattr(m.os,'fstat',changed)
        with pytest.raises(m.BindingError,match='carrier_changed_during_read'):reader.read('one','one')


def test_wp2a_installed_schema_failure_is_not_a_success_report(monkeypatch,capsys):
    m=_wp2_module()
    def unavailable():raise OSError('fixture installation failure')
    monkeypatch.setattr(m,'SchemaSet',unavailable)
    result=m.main(['--bundle-root',str(WP2_DEMO),'--input','input.json','--expected-input-sha256',WP2_INPUT_PIN,'--carriers','carriers.json','--expected-carriers-sha256',WP2_CARRIERS_PIN])
    captured=capsys.readouterr();assert result==2 and not captured.out
    assert 'installation error' in captured.err


def test_wp2a_recorded_negative_source_labels_are_not_rewritten(tmp_path):
    root=_wp2_fixture(tmp_path);p=root/'evidence.json';d=load_json(p)
    d['sources'][0]['identity_verification']={'status':'completed','result':'mismatch','reason':'recorded external mismatch'}
    _wp2_write(p,d);pins=_wp2_rebind(root);before=p.read_bytes();report=_wp2_run(root,pins)
    assert report['status']=='LOCAL_BINDINGS_CONSISTENT'
    assert p.read_bytes()==before
    _wp2_assert_limits(report)


@pytest.mark.parametrize('part',('source_identity_authentication','typed_evidence_cycle_check','semantic_support_verification','response_mode_recommendation'))
def test_wp2a_report_schema_rejects_nonrun_measured_results(part):
    report=_wp2_run(WP2_DEMO);report['unperformed_checks'][part]['result']='verified'
    with pytest.raises(_wp2_module().BindingError):_wp2_module().SchemaSet().validate('report',report)



# WP2B: explicit JSON-pointer projection. All preceding WP1/WP2A tests remain.
WP2B_DEMO = EXAMPLE_DIR / "wp2b_json_pointer"
WP2B_INPUT_PIN = "2551b182d5b31477d94df8cadf94a38120499d4ebe72b780dd1f00b1fa7e605a"
WP2B_CARRIERS_PIN = "dbed53cc547ea242cf3ef5111513b65dd8dd23a80d1994784a7c98ebf65be19e"


@_wp2_lru_cache(maxsize=1)
def _wp2b_pointer_module():
    path = ROOT / "tools" / "anchor_integrity_json_pointer_v0_1.py"
    spec = _wp2_importlib.spec_from_file_location("anchor_wp2b_projection_test", path)
    module = _wp2_importlib.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _wp2b_fixture(tmp_path):
    dest = tmp_path / "json-bundle"
    _wp2_shutil.copytree(WP2B_DEMO, dest)
    return dest


def _wp2b_run(root, pins=None):
    first, second = pins or (WP2B_INPUT_PIN, WP2B_CARRIERS_PIN)
    m = _wp2_module()
    return m.verify_bundle(root, "input.json", first, "carriers.json", second,
                           profile=m.WP2B_PROFILE)


def _wp2b_assert_limits(report):
    assert report["schema_version"] == "anchor_integrity_binding_report_v0_2"
    assert report["work_package"] == "WP2B"
    assert report["json_pointer_profile"] == "rfc6901_source_spans_v1"
    assert report["candidate_status"] == "diagnostic_only"
    assert report["authority_effect"] == "none"
    assert report["release_authority_activation"] is False
    assert report["requested_checks_complete"] is False
    for check in report["unperformed_checks"].values():
        assert check["status"] == "not_run" and check["result"] is None
    for check in report["checks"]:
        if check["status"] != "completed":
            assert check["result"] is None and check["reason"]
    for relation in report["recorded_relation_results"]:
        assert relation["accepted_as_semantic_support"] is False
    m = _wp2_module()
    m.SchemaSet(m.WP2B_PROFILE).validate("report", report)


def test_wp2b_complete_demo_receipts_and_explicit_pins():
    assert _wp2_hash(WP2B_DEMO / "input.json") == WP2B_INPUT_PIN
    assert _wp2_hash(WP2B_DEMO / "carriers.json") == WP2B_CARRIERS_PIN
    report = _wp2b_run(WP2B_DEMO)
    assert report["status"] == "LOCAL_BINDINGS_CONSISTENT"
    assert report["issues"] == []
    assert report["counts"]["claims"] == 2
    receipts = report["json_pointer_selections"]
    assert len(receipts) == 3
    assert receipts[-1]["projected_sha256"] == hashlib.sha256(b"7.00e+0").hexdigest()
    assert receipts[0]["source_slice_sha256"] != receipts[0]["projected_sha256"]
    assert receipts[0]["projected_sha256"] == hashlib.sha256(b"The recorded sample value is 7.").hexdigest()
    for receipt in receipts:
        data = (WP2B_DEMO / ("response.json" if receipt["purpose"] == "claim" else "source.json")).read_bytes()
        raw = data[receipt["start_byte"]:receipt["end_byte"]]
        assert hashlib.sha256(raw).hexdigest() == receipt["source_slice_sha256"]
        assert hashlib.sha256(data).hexdigest() == receipt["source_sha256"]
    assert report["implementation"]["json_pointer_module_sha256"] == _wp2_hash(
        ROOT / "tools/anchor_integrity_json_pointer_v0_1.py")
    _wp2b_assert_limits(report)


@pytest.mark.parametrize("schema", ("anchor_integrity_local_carriers_v0_2.schema.json", "anchor_integrity_binding_report_v0_2.schema.json"))
def test_wp2b_new_schema_valid_and_self_contained(schema):
    value = load_json(SCHEMA_DIR / schema)
    jsonschema.Draft202012Validator.check_schema(value)
    _wp2_module()._assert_self_contained(value)


def test_wp2b_is_not_implicitly_enabled_for_v02_carriers():
    report = _wp2_run(WP2B_DEMO, (WP2B_INPUT_PIN, WP2B_CARRIERS_PIN))
    assert report["status"] == "LOCAL_BINDINGS_INVALID"
    assert _wp2_issue(report, "schema_invalid_carriers")
    assert "json_pointer_selections" not in report
    _wp2_assert_limits(report)


def test_wp2b_requires_v02_carrier_and_never_falls_back_to_v01():
    report = _wp2b_run(WP2_DEMO, (WP2_INPUT_PIN, WP2_CARRIERS_PIN))
    assert report["status"] == "LOCAL_BINDINGS_INVALID"
    assert _wp2_issue(report, "schema_invalid_carriers")
    _wp2b_assert_limits(report)


def test_wp2b_old_profile_keeps_json_pointer_incomplete(tmp_path):
    root = _wp2b_fixture(tmp_path)
    carrier = load_json(root / "carriers.json")
    carrier["schema_version"] = "anchor_integrity_local_carriers_v0_1"
    del carrier["json_pointer_profile"]
    _wp2_write(root / "carriers.json", carrier)
    report = _wp2_run(root, (WP2B_INPUT_PIN, _wp2_hash(root / "carriers.json")))
    assert report["status"] == "LOCAL_BINDINGS_INCOMPLETE"
    assert _wp2_issue(report, "json_pointer_projection_not_implemented")
    _wp2_assert_limits(report)


@pytest.mark.parametrize("value", (None, "", "unknown", "rfc6901_source_spans_v2", True, 1))
def test_wp2b_wrong_or_missing_profile_is_rejected(tmp_path, value):
    root = _wp2b_fixture(tmp_path)
    p = root / "carriers.json"; carrier = load_json(p)
    if value is None:
        del carrier["json_pointer_profile"]
    else:
        carrier["json_pointer_profile"] = value
    _wp2_write(p, carrier)
    report = _wp2b_run(root, (WP2B_INPUT_PIN, _wp2_hash(p)))
    assert report["status"] == "LOCAL_BINDINGS_INVALID"
    assert _wp2_issue(report, "schema_invalid_carriers")
    _wp2b_assert_limits(report)


@pytest.mark.parametrize("pointer,token,kind", (
    ("/list/0", b'"first"', "string"),
    ("/list", b'["first", "second"]', "array"),
    ("/", b"9", "number"),
    ("/a~1b", b"1", "number"),
    ("/tilde~0key", b"2", "number"),
    ("/c%d", b"3", "number"),
    ("/~01", b"4", "number"),
    ("/~1", b"5", "number"),
    ("/01", b"6", "number"),
    ("/-", b"7", "number"),
    ("/~0", b"8", "number"),
))
def test_wp2b_pointer_token_rules_and_object_numeric_keys(pointer, token, kind):
    # Original fixture; covers the escaping and evaluation rules of RFC 6901.
    raw = b'{"list": ["first", "second"], "":9, "a/b":1, "tilde~key":2, "c%d":3, "~1":4, "/":5, "01":6, "-":7, "~":8}'
    selected, receipt = _wp2b_pointer_module().Document(raw).project(pointer, "evidence")
    assert selected == token and receipt["selected_value_type"] == kind
    assert raw[receipt["start_byte"]:receipt["end_byte"]] == token


@pytest.mark.parametrize("token,kind", (
    (b"null", "null"), (b"true", "boolean"), (b"false", "boolean"),
    (b"0", "number"), (b"-0", "number"), (b"1.000e+02", "number"),
    (b"1e99999", "number"), (b"-1e-99999", "number"),
    (b"123456789012345678901234567890", "number"),
    (b'"\\u0061"', "string"), (b'"a\\/b"', "string"),
    (b'""', "string"), (b"[]", "array"), (b"{}", "object"),
    (b'[ 1,\n 2 ]', "array"), (b'{ "z" : 1, "a" : 2 }', "object"),
))
def test_wp2b_evidence_preserves_exact_lexeme(token, kind):
    raw = b' \r\n { "x" : \t' + token + b' \n}  '
    selected, receipt = _wp2b_pointer_module().Document(raw).project("/x", "evidence")
    assert selected == token
    assert receipt["selected_value_type"] == kind
    assert receipt["projection"] == "source_value_bytes"
    assert receipt["projected_sha256"] == hashlib.sha256(token).hexdigest()
    assert raw[receipt["start_byte"]:receipt["end_byte"]] == token


@pytest.mark.parametrize("token,decoded", (
    (b'"simple"', "simple"), (b'"\\u0061"', "a"),
    (b'"\\u00e1rv\\u00edz"', "árvíz"),
    ('"árvíz"'.encode(), "árvíz"),
    (b'"\\ud83d\\ude00"', "😀"), ('"😀"'.encode(), "😀"),
    (b'"a\\n\\t\\r\\b\\f\\u0000"', "a\n\t\r\b\f\0"),
    (b'"a\\\\b\\/c\\\"d"', 'a\\b/c"d'),
    ('"e\u0301"'.encode(), "e\u0301"), (b'""', ""),
))
def test_wp2b_claim_projection_decodes_strings_only_without_normalization(token, decoded):
    raw = ' {"prefix":"😀", "claim": '.encode() + token + b"}"
    selected, receipt = _wp2b_pointer_module().Document(raw).project("/claim", "claim")
    assert selected == decoded.encode("utf-8")
    assert receipt["projection"] == "decoded_string_utf8"
    assert raw[receipt["start_byte"]:receipt["end_byte"]] == token


@pytest.mark.parametrize("token", (b"1", b"null", b"false", b"true", b"[]", b"{}"))
def test_wp2b_claim_projection_does_not_stringify_other_json_types(token):
    m = _wp2b_pointer_module()
    with pytest.raises(m.ProjectionError, match="^json_pointer_claim_requires_string$"):
        m.Document(b'{"x":' + token + b'}').project("/x", "claim")


@pytest.mark.parametrize("pointer,code", (
    ("x", "json_pointer_syntax"), ("#/x", "json_pointer_syntax"),
    ("/~", "json_pointer_syntax"), ("/~2", "json_pointer_syntax"),
    ("/~~0", "json_pointer_syntax"), ("/x~01~", "json_pointer_syntax"),
    ("/missing", "json_pointer_member_missing"),
    ("/list/00", "json_pointer_array_index"), ("/list/01", "json_pointer_array_index"),
    ("/list/-", "json_pointer_array_index"), ("/list/-1", "json_pointer_array_index"),
    ("/list/+0", "json_pointer_array_index"), ("/list/ 0", "json_pointer_array_index"),
    ("/list/٠", "json_pointer_array_index"), ("/list/０", "json_pointer_array_index"),
    ("/list/0.0", "json_pointer_array_index"), ("/list/1e0", "json_pointer_array_index"),
    ("/list/", "json_pointer_array_index"),
    ("/list/1", "json_pointer_index_out_of_bounds"),
    ("/list/" + "9" * 500, "json_pointer_index_out_of_bounds"),
    ("/list/0/x", "json_pointer_scalar_traversal"),
    ("/null/x", "json_pointer_scalar_traversal"),
    ("/empty/0", "json_pointer_index_out_of_bounds"),
    ("/a%2Fb", "json_pointer_member_missing"),
    ("/e\u0301", "json_pointer_member_missing"),
))
def test_wp2b_bad_pointers_have_stable_errors(pointer, code):
    m = _wp2b_pointer_module()
    raw = '{"list":[1],"null":null,"empty":[],"a/b":2,"é":3}'.encode()
    with pytest.raises(m.ProjectionError) as exc:
        m.Document(raw).project(pointer, "evidence")
    assert exc.value.code == code


@pytest.mark.parametrize("pointer", (None, 0, True, [], {}))
def test_wp2b_pointer_must_be_a_string(pointer):
    m = _wp2b_pointer_module()
    with pytest.raises(m.ProjectionError, match="^json_pointer_type$"):
        m.Document(b'{}').project(pointer, "evidence")


@pytest.mark.parametrize("raw", (
    b'', b' ', b'{', b'[', b'{"x":}', b'{x:1}', b'{"x" 1}',
    b'{"x":1,}', b'[1,]', b'[,1]', b'[1 2]', b'{"x":1 "y":2}',
    b'true false', b'{}x', b'{"x":01}', b'{"x":-01}', b'{"x":+1}',
    b'{"x":1.}', b'{"x":.1}', b'{"x":1e}', b'{"x":1e+}',
    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":TRUE}',
    b'/*comment*/{}', b'{"x":1//x\n}', b'{"x":1\x0b}',
    b'"unterminated', b'"bad\\q"', b'"bad\\u000x"', b'"bad\n"',
    b'"bad\x00"', b'"bad\\"', b'"\\ud800"', b'"\\udc00"',
    b'"\\ud800x"', b'"\\ud800\\u0061"', b'{"\\ud800":1}',
    b'\xef\xbb\xbf{}', b'\xff', b'{"x":"\xc0\xaf"}', b'{"x":"\xed\xa0\x80"}',
))
def test_wp2b_entire_json_document_is_checked(raw):
    m = _wp2b_pointer_module()
    with pytest.raises(m.ProjectionError):
        m.Document(raw)


@pytest.mark.parametrize("raw", (
    b'{"a":1,"a":2}', b'{"a":1,"\\u0061":2}',
    b'{"ok":1,"discarded":{"x":1,"x":2}}',
    b'{"ok":1,"discarded":[{"x":1,"\\u0078":2}]}',
    '{"😀":1,"\\ud83d\\ude00":2}'.encode(),
))
def test_wp2b_duplicate_decoded_keys_anywhere_are_rejected(raw):
    m = _wp2b_pointer_module()
    with pytest.raises(m.ProjectionError, match="^json_pointer_duplicate_key$"):
        m.Document(raw)


@pytest.mark.parametrize("key", ("", "a/b", "~", "~1", "a%b", "\0", "\n", "\"", "\\", "árvíz", "😀", "e\u0301"))
def test_wp2b_member_keys_resolve_by_code_points(key):
    raw = json.dumps({key: "value"}, ensure_ascii=True).encode()
    pointer = "/" + key.replace("~", "~0").replace("/", "~1")
    projected, receipt = _wp2b_pointer_module().Document(raw).project(pointer, "claim")
    assert projected == b"value"
    assert raw[receipt["start_byte"]:receipt["end_byte"]] == b'"value"'


def test_wp2b_root_utility_support_does_not_relax_existing_packet_schemas(tmp_path):
    m = _wp2b_pointer_module()
    assert m.Document(b' \n [ 1 ] ').project("", "evidence")[0] == b'[ 1 ]'
    root = _wp2b_fixture(tmp_path); p = root / "claims.json"; cp = load_json(p)
    cp['claim_set']['claims'][0]['locator']['value'] = ""
    _wp2_write(p, cp)
    report = _wp2b_run(root, _wp2_rebind(root))
    assert report['status'] == 'LOCAL_BINDINGS_INVALID'
    assert _wp2_issue(report, 'schema_invalid_claims')


@pytest.mark.parametrize("limit,value,raw,code", (
    ("MAX_FILE_BYTES", 2, b"[0]", "json_pointer_file_limit"),
    ("MAX_DEPTH", 2, b"[[[0]]]", "json_pointer_complexity_limit"),
    ("MAX_NODES", 2, b"[0,1]", "json_pointer_complexity_limit"),
    ("MAX_NODES", 2, b'{"a":1}', "json_pointer_complexity_limit"),
    ("MAX_ITEMS", 1, b"[0,1]", "json_pointer_item_limit"),
    ("MAX_ITEMS", 1, b'{"a":1,"b":2}', "json_pointer_item_limit"),
))
def test_wp2b_document_resource_limits(limit, value, raw, code, monkeypatch):
    m = _wp2b_pointer_module(); monkeypatch.setattr(m, limit, value)
    with pytest.raises(m.ProjectionError) as exc:
        m.Document(raw)
    assert exc.value.code == code


def test_wp2b_document_at_exact_limits_is_accepted(monkeypatch):
    m = _wp2b_pointer_module()
    monkeypatch.setattr(m, "MAX_FILE_BYTES", 3)
    monkeypatch.setattr(m, "MAX_DEPTH", 1)
    monkeypatch.setattr(m, "MAX_ITEMS", 1)
    monkeypatch.setattr(m, "MAX_NODES", 2)
    assert m.Document(b"[0]").project("/0", "evidence")[0] == b"0"


@pytest.mark.parametrize("pointer,code", (
    ("/" + "x" * 4096, "json_pointer_length_limit"),
    ("/" + "é" * 2048, "json_pointer_length_limit"),
    ("/a" * 65, "json_pointer_token_limit"),
    ("/\ud800", "json_pointer_invalid_unicode"),
))
def test_wp2b_pointer_limits(pointer, code):
    m = _wp2b_pointer_module()
    with pytest.raises(m.ProjectionError) as exc:
        m.Document(b"{}").project(pointer, "evidence")
    assert exc.value.code == code


@pytest.mark.parametrize("value", ("x", b"x", None, True))
def test_wp2b_unknown_projection_purpose_is_rejected(value):
    m = _wp2b_pointer_module()
    with pytest.raises(m.ProjectionError, match="^json_pointer_projection_purpose$"):
        m.Document(b'{}').project("", value)


@pytest.mark.parametrize("filename", ("input.json", "carriers.json", "claims.json", "evidence.json", "relations.json", "legacy.json", "response.json", "source.json"))
def test_wp2b_missing_carriers_are_incomplete(tmp_path, filename):
    root = _wp2b_fixture(tmp_path); (root / filename).unlink()
    report = _wp2b_run(root)
    assert report["status"] == "LOCAL_BINDINGS_INCOMPLETE"
    assert _wp2_issue(report, "missing_carrier")
    _wp2b_assert_limits(report)


@pytest.mark.parametrize("filename", ("input.json", "carriers.json", "claims.json", "evidence.json", "relations.json", "legacy.json", "response.json", "source.json"))
def test_wp2b_stale_root_or_source_hash_is_invalid(tmp_path, filename):
    root = _wp2b_fixture(tmp_path); p = root / filename
    p.write_bytes(p.read_bytes() + b"\n")
    report = _wp2b_run(root)
    assert report["status"] == "LOCAL_BINDINGS_INVALID"
    _wp2b_assert_limits(report)


@pytest.mark.parametrize("target,pointer,code", (
    ("claims", "/statements/01", "json_pointer_array_index"),
    ("claims", "/kind/0", "json_pointer_scalar_traversal"),
    ("evidence", "/record/missing", "json_pointer_member_missing"),
    ("evidence", "/record/~2", "json_pointer_syntax"),
))
def test_wp2b_bad_locator_remains_invalid_after_outer_rehash(tmp_path, target, pointer, code):
    root = _wp2b_fixture(tmp_path); p = root / (target + ".json"); obj = load_json(p)
    if target == 'claims':obj['claim_set']['claims'][0]['locator']['value'] = pointer
    else: obj['evidence_items'][0]['locator']['value'] = pointer
    _wp2_write(p, obj); report = _wp2b_run(root, _wp2_rebind(root))
    assert report['status'] == 'LOCAL_BINDINGS_INVALID' and _wp2_issue(report, code)
    _wp2b_assert_limits(report)


def test_wp2b_rehashing_source_does_not_hide_changed_selected_lexeme(tmp_path):
    root = _wp2b_fixture(tmp_path); source = root / 'source.json'
    source.write_bytes(source.read_bytes().replace(b'7.00e+0', b'7'))
    p = root / 'evidence.json'; ep = load_json(p)
    ep['sources'][0]['content_sha256'] = _wp2_hash(source)
    _wp2_write(p, ep)
    report = _wp2b_run(root, _wp2_rebind(root))
    assert report['status'] == 'LOCAL_BINDINGS_INVALID'
    assert any(x['id']=='evidence:evidence-1.sha256' and x['result']=='mismatch' for x in report['checks'])
    _wp2b_assert_limits(report)


def test_wp2b_unchanged_selection_does_not_hide_changed_whole_source(tmp_path):
    root = _wp2b_fixture(tmp_path); source = root / 'source.json'
    source.write_bytes(source.read_bytes().replace(b'false', b'true'))
    report = _wp2b_run(root)
    assert report['status'] == 'LOCAL_BINDINGS_INVALID'
    assert any(x['id'].startswith('source:') and x['id'].endswith('.sha256') and x['result']=='mismatch' for x in report['checks'])
    assert any(x['id']=='evidence:evidence-1.sha256' and x['result']=='match' for x in report['checks'])


@pytest.mark.parametrize('bad', (b'{"record":{"value":7.00e+0},"outside":{"x":1,"x":2}}', b'{"record":{"value":7.00e+0}} trailing'))
def test_wp2b_rehashed_malformed_source_cannot_pass(tmp_path, bad):
    root=_wp2b_fixture(tmp_path);(root/'source.json').write_bytes(bad)
    p=root/'evidence.json';ep=load_json(p);ep['sources'][0]['content_sha256']=_wp2_hash(root/'source.json')
    _wp2_write(p,ep);report=_wp2b_run(root,_wp2_rebind(root))
    assert report['status']=='LOCAL_BINDINGS_INVALID'
    assert not any(x['purpose']=='evidence' for x in report['json_pointer_selections'])
    _wp2b_assert_limits(report)


def test_wp2b_invalid_wins_over_missing_carrier(tmp_path):
    root=_wp2b_fixture(tmp_path);(root/'response.json').unlink()
    (root/'source.json').write_bytes(b'invalid')
    report=_wp2b_run(root)
    assert report['status']=='LOCAL_BINDINGS_INVALID'
    assert {x['severity'] for x in report['issues']}=={'invalid','incomplete'}
    _wp2b_assert_limits(report)


def test_wp2b_report_determinism_and_input_non_interference(tmp_path):
    root=_wp2b_fixture(tmp_path);before={p.name:p.read_bytes() for p in root.iterdir()}
    a=_wp2b_run(root);b=_wp2b_run(root)
    assert json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True)
    assert before=={p.name:p.read_bytes() for p in root.iterdir()}
    _wp2b_assert_limits(a)


def test_wp2b_line_and_character_locators_still_work_in_explicit_profile(tmp_path):
    root=_wp2_fixture(tmp_path);p=root/'carriers.json';ca=load_json(p)
    ca['schema_version']='anchor_integrity_local_carriers_v0_2'
    ca['json_pointer_profile']='rfc6901_source_spans_v1';_wp2_write(p,ca)
    report=_wp2b_run(root,(WP2_INPUT_PIN,_wp2_hash(p)))
    assert report['status']=='LOCAL_BINDINGS_CONSISTENT'
    assert report['json_pointer_selections']==[]
    _wp2b_assert_limits(report)


@pytest.mark.parametrize('field,value', (('requested_checks_complete',True),('authority_effect','release'),('release_authority_activation',True),('candidate_status','active')))
def test_wp2b_report_cannot_promote_authority(field,value):
    report=_wp2b_run(WP2B_DEMO);report[field]=value;m=_wp2_module()
    with pytest.raises(m.BindingError):m.SchemaSet(m.WP2B_PROFILE).validate('report',report)


@pytest.mark.parametrize('part',_wp2_module().UNPERFORMED)
def test_wp2b_report_does_not_promote_unperformed_checks(part):
    report=_wp2b_run(WP2B_DEMO);report['unperformed_checks'][part]['status']='completed'
    report['unperformed_checks'][part]['result']='verified';m=_wp2_module()
    with pytest.raises(m.BindingError):m.SchemaSet(m.WP2B_PROFILE).validate('report',report)


@pytest.mark.parametrize('mutation',('claim_projection','claim_type','evidence_projection','module_hash','profile'))
def test_wp2b_report_rejects_wrong_projection_identity(mutation):
    report=_wp2b_run(WP2B_DEMO)
    if mutation=='claim_projection':report['json_pointer_selections'][0]['projection']='source_value_bytes'
    elif mutation=='claim_type':report['json_pointer_selections'][0]['selected_value_type']='number'
    elif mutation=='evidence_projection':report['json_pointer_selections'][-1]['projection']='decoded_string_utf8'
    elif mutation=='module_hash':del report['implementation']['json_pointer_module_sha256']
    else:report['json_pointer_profile']='other'
    m=_wp2_module()
    with pytest.raises(m.BindingError):m.SchemaSet(m.WP2B_PROFILE).validate('report',report)


def test_wp2b_parser_is_cached_per_exact_source_and_errors_cached(monkeypatch):
    m=_wp2_module();review=m.Review(m.SchemaSet(m.WP2B_PROFILE));module=review._pointer_module
    calls=[];original=module.Document
    def counted(data):
        calls.append(data);return original(data)
    monkeypatch.setattr(module,'Document',counted)
    raw=b'{"x":"ok","y":"also"}'
    for i in range(2):
        assert review.select(raw,{'type':'json_pointer','value':'/x'},'claim',f'c{i}')==b'ok'
    bad=b'{broken'
    for i in range(2):
        with pytest.raises(m.BindingError):review.select(bad,{'type':'json_pointer','value':'/x'},'claim',f'e{i}')
    assert calls==[raw,bad]


def test_wp2b_projection_byte_budget_is_enforced(monkeypatch):
    m=_wp2_module();monkeypatch.setattr(m,'MAX_POINTER_PROJECTION_BYTES',1)
    report=_wp2b_run(WP2B_DEMO)
    assert report['status']=='LOCAL_BINDINGS_INVALID'
    assert _wp2_issue(report,'json_pointer_projection_budget')
    assert report['json_pointer_selections']==[]


def test_wp2b_projection_module_import_does_not_write_bytecode(tmp_path,monkeypatch):
    m=_wp2_module();root=tmp_path/'installation';(root/'tools').mkdir(parents=True)
    _wp2_shutil.copytree(ROOT/'schemas',root/'schemas')
    _wp2_shutil.copyfile(ROOT/'tools/anchor_integrity_json_pointer_v0_1.py',root/'tools/anchor_integrity_json_pointer_v0_1.py')
    monkeypatch.setattr(m,'ROOT',root);previous=_wp2_sys.dont_write_bytecode
    m.Review(m.SchemaSet(m.WP2B_PROFILE))
    assert _wp2_sys.dont_write_bytecode==previous
    assert not (root/'tools/__pycache__').exists()


def test_wp2b_unknown_cli_profile_fails_without_success_json():
    result=_wp2_subprocess.run([_wp2_sys.executable,str(WP2_TOOL),'--bundle-root',str(WP2B_DEMO),'--input','input.json','--expected-input-sha256',WP2B_INPUT_PIN,'--carriers','carriers.json','--expected-carriers-sha256',WP2B_CARRIERS_PIN,'--profile','unrecognized'],capture_output=True,timeout=30)
    assert result.returncode==2 and not result.stdout


def test_wp2b_full_cli_returns_bounded_diagnostic_report():
    result=_wp2_subprocess.run([_wp2_sys.executable,str(WP2_TOOL),'--bundle-root',str(WP2B_DEMO),'--input','input.json','--expected-input-sha256',WP2B_INPUT_PIN,'--carriers','carriers.json','--expected-carriers-sha256',WP2B_CARRIERS_PIN,'--profile','wp2b-json-pointer-v1'],capture_output=True,timeout=30)
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout);assert report['status']=='LOCAL_BINDINGS_CONSISTENT'
    _wp2b_assert_limits(report)


def test_wp2b_test_registration_reuses_existing_module():
    for name in ('ci/tools-tests.list','ci/pytest-tests.list'):
        entries=_manifest_entries(ROOT/name)
        assert entries.count(TEST_PATH)==1


def test_wp2b_projection_matches_independent_json_values_over_generated_trees():
    # A deterministic synthetic corpus; compare resolution to JSON's decoded
    # values while independently checking original token slices and receipts.
    import random
    rng=random.Random(4297)
    m=_wp2b_pointer_module()
    def tree(depth):
        if depth==0 or rng.randrange(3)==0:return rng.choice([None,True,False,0,-3,1.25,'a/b','~1','árvíz','😀','e\u0301'])
        if rng.randrange(2):return [tree(depth-1) for _ in range(rng.randrange(4))]
        return {str(i)+rng.choice(['/','~','é','']):tree(depth-1) for i in range(rng.randrange(4))}
    def walk(v,pointer=''):
        yield pointer,v
        if isinstance(v,dict):
            for k,x in v.items():yield from walk(x,pointer+'/'+k.replace('~','~0').replace('/','~1'))
        elif isinstance(v,list):
            for i,x in enumerate(v):yield from walk(x,pointer+'/'+str(i))
    count=0
    for _ in range(80):
        value=tree(4)
        data=json.dumps(value,ensure_ascii=bool(rng.randrange(2)),indent=rng.choice([None,1,2])).encode()
        doc=m.Document(data)
        for pointer,expected in walk(value):
            raw,receipt=doc.project(pointer,'evidence')
            assert json.loads(raw)==expected
            assert raw==data[receipt['start_byte']:receipt['end_byte']]
            if isinstance(expected,str):assert doc.project(pointer,'claim')[0]==expected.encode()
            count+=1
    assert count>=200


# WP2C: materialized verifier-record bindings. No declaration becomes proof.
import importlib.util as _wp2c_importlib
import os as _wp2c_os
import shutil as _wp2c_shutil
import subprocess as _wp2c_subprocess
import sys as _wp2c_sys

WP2C_TOOL = ROOT / 'tools/check_anchor_integrity_verifier_records_v0_1.py'
WP2C_DEMO = ROOT / 'examples/anchor_integrity_v0_1/wp2c_verifier_records'
WP2C_INPUT_PIN = 'd7d16dfccf2dce237060e6b77fbb7da907227b1bd56f1275cfb623ce81cd59a8'
WP2C_CARRIERS_PIN = '70a4d15ee35db21a605ef283c531724d921658fa8bc46ca68f6867925b2c91c4'
WP2C_SET_PIN = 'a70299602a9aae82adcd4ff17278eef5a802ad72e05dbdae6fec64a9f98f188e'


def _wp2c_module():
    spec = _wp2c_importlib.spec_from_file_location('wp2c_test_checker', WP2C_TOOL)
    module = _wp2c_importlib.module_from_spec(spec)
    previous = _wp2c_sys.dont_write_bytecode
    _wp2c_sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        _wp2c_sys.dont_write_bytecode = previous
    return module


def _wp2c_write(root, name, data):
    (root / name).write_text(json.dumps(data, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def _wp2c_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wp2c_fixture(tmp_path):
    root = tmp_path / 'records'
    _wp2c_shutil.copytree(WP2C_DEMO, root)
    return root


def _wp2c_pins(root):
    return tuple(_wp2c_hash(root / n) for n in ('input.json', 'carriers.json', 'record-set.json'))


def _wp2c_repin(root, sync_record_roots=False):
    """Rehash outer layers; do not fix inner binding assertions implicitly."""
    rp = load_json(root / 'relations.json')
    for k, f in [('claim_packet_binding', 'claims.json'), ('evidence_packet_binding', 'evidence.json')]:
        rp[k]['sha256'] = _wp2c_hash(root / f)
    _wp2c_write(root, 'relations.json', rp)
    inp = load_json(root / 'input.json')
    for k, f in [('claim_packet', 'claims.json'), ('evidence_packet', 'evidence.json'), ('relation_verification_packet', 'relations.json')]:
        inp['packet_bindings'][k]['sha256'] = _wp2c_hash(root / f)
    _wp2c_write(root, 'input.json', inp)
    ca = load_json(root / 'carriers.json'); ca['input_sha256'] = _wp2c_hash(root / 'input.json')
    _wp2c_write(root, 'carriers.json', ca)
    rs = load_json(root / 'record-set.json')
    rs['input_binding']['sha256'] = _wp2c_hash(root / 'input.json')
    rs['carriers_binding']['sha256'] = _wp2c_hash(root / 'carriers.json')
    for e in rs['records']:
        path = root / e['path']
        if path.is_file() and not path.is_symlink():
            if sync_record_roots:
                record = load_json(path)
                record.update(input_sha256=_wp2c_hash(root/'input.json'), carriers_sha256=_wp2c_hash(root/'carriers.json'),
                              packet_sha256={k:_wp2c_hash(root/n) for k,n in [('claims','claims.json'),('evidence','evidence.json'),('relations','relations.json')]})
                _wp2c_write(root, e['path'], record)
            e['sha256'] = _wp2c_hash(path)
    _wp2c_write(root, 'record-set.json', rs)
    return _wp2c_pins(root)


def _wp2c_run(root=WP2C_DEMO, pins=None, profile='wp2b-json-pointer-v1', module=None):
    if pins is None: pins = (WP2C_INPUT_PIN, WP2C_CARRIERS_PIN, WP2C_SET_PIN)
    m = module or _wp2c_module()
    return m.verify_records(root, 'input.json', pins[0], 'carriers.json', pins[1],
                            'record-set.json', pins[2], binding_profile=profile)


def _wp2c_limits(report):
    assert report['candidate_status'] == 'diagnostic_only'
    assert report['authority_effect'] == 'none'
    assert report['release_authority_activation'] is False
    assert report['requested_checks_complete'] is False
    assert report['accepted_as_semantic_support'] is False
    for check in report['unperformed_checks'].values():
        assert check['status'] == 'not_run' and check['result'] is None and check['reason']
    for row in report['records']: assert row['accepted_as_semantic_support'] is False
    m = _wp2c_module(); m.RecordSchemas(m.load_binding_checker()).validate('report', report)


def _wp2c_has(report, code):
    return any(x['code'] == code for x in report['issues'])


def test_wp2c_complete_synthetic_record_is_locally_matched_not_authenticated():
    r = _wp2c_run()
    assert r['status'] == 'LOCAL_RECORD_BINDINGS_CONSISTENT'
    assert r['counts'] == {'completed_relations':1,'listed_records':1,'matching_records':1}
    assert r['records'][0]['declared_result'] == 'unresolved'
    assert r['records'][0]['expected_sha256'] == r['records'][0]['observed_sha256']
    assert r['base_check']['status'] == 'LOCAL_BINDINGS_CONSISTENT'
    _wp2c_limits(r)


@pytest.mark.parametrize('which', range(3))
@pytest.mark.parametrize('digest_value', ['0'*64, 'invalid', '', 'A'*64])
def test_wp2c_rejects_missing_or_wrong_external_expectations(which, digest_value):
    pins = [WP2C_INPUT_PIN,WP2C_CARRIERS_PIN,WP2C_SET_PIN]; pins[which] = digest_value
    r = _wp2c_run(pins=pins)
    assert r['status'] == 'LOCAL_RECORD_BINDINGS_INVALID'
    assert r['counts']['matching_records'] is None
    _wp2c_limits(r)


@pytest.mark.parametrize('name', ['record-set.json','input.json','carriers.json','claims.json','evidence.json','relations.json','response.json','source.json','legacy.json','record-1.json'])
def test_wp2c_missing_carriers_never_match(tmp_path, name):
    root = _wp2c_fixture(tmp_path); (root/name).unlink(); r = _wp2c_run(root)
    assert r['status'] == 'LOCAL_RECORD_BINDINGS_INCOMPLETE'
    assert r['counts']['matching_records'] in (None,0)
    _wp2c_limits(r)


@pytest.mark.parametrize('path', ['../record-1.json','/tmp/record.json','a//b','./record.json','x/../record.json','a\\b','https://invalid/record','record.json.'])
def test_wp2c_unsafe_record_paths_rejected(tmp_path, path):
    root=_wp2c_fixture(tmp_path);rs=load_json(root/'record-set.json');rs['records'][0]['path']=path
    _wp2c_write(root,'record-set.json',rs);r=_wp2c_run(root,_wp2c_pins(root))
    assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'


@pytest.mark.parametrize('path',['input.json','carriers.json','record-set.json','claims.json','evidence.json','relations.json','response.json','source.json','legacy.json'])
def test_wp2c_record_cannot_reuse_any_checked_input_role(tmp_path,path):
    root=_wp2c_fixture(tmp_path);rs=load_json(root/'record-set.json');rs['records'][0]['path']=path
    rs['records'][0]['sha256']=_wp2c_hash(root/path);_wp2c_write(root,'record-set.json',rs)
    r=_wp2c_run(root,_wp2c_pins(root));assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert r['counts']['matching_records'] is None


@pytest.mark.parametrize('kind',['duplicate_record_id','duplicate_binding_id','reused_path','case_collision'])
def test_wp2c_manifest_uniqueness_checks(tmp_path,kind):
    root=_wp2c_fixture(tmp_path);rs=load_json(root/'record-set.json');entry=deepcopy(rs['records'][0])
    entry.update(record_id='second-record',binding_id='second-binding',path='second.json')
    if kind=='duplicate_record_id':entry['record_id']=rs['records'][0]['record_id']
    elif kind=='duplicate_binding_id':entry['binding_id']=rs['records'][0]['binding_id']
    elif kind=='reused_path':entry['path']='record-1.json'
    else:entry['path']='RECORD-1.json'
    rs['records'].append(entry);_wp2c_write(root,'record-set.json',rs)
    r=_wp2c_run(root,_wp2c_pins(root));assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'


@pytest.mark.parametrize('key,value',[('profile','other'),('binding_profile','wp2a'),('input_binding',{'path':'other.json','sha256':'0'*64}),('carriers_binding',{'path':'carriers.json','sha256':'0'*64}),('candidate_status','active'),('authority_effect','release'),('release_authority_activation',True),('extra','value')])
def test_wp2c_record_set_profile_roots_and_boundary_are_explicit(tmp_path,key,value):
    root=_wp2c_fixture(tmp_path);rs=load_json(root/'record-set.json');rs[key]=value
    _wp2c_write(root,'record-set.json',rs);r=_wp2c_run(root,_wp2c_pins(root))
    assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'


@pytest.mark.parametrize('field',[
 'record_id','subject.subject_id','subject.run_id','input_sha256','carriers_sha256',
 'packet_sha256.claims','packet_sha256.evidence','packet_sha256.relations',
 'binding.binding_id','binding.claim_id','binding.claim_digest','binding.evidence_id',
 'binding.source_id','binding.source_sha256','binding.evidence_sha256','binding.relation_type',
 'verifier.verifier_id','verifier.method_id','verifier.method_version','verifier.implementation_sha256',
 'verification.result','verification.reason'])
def test_wp2c_rehashed_record_must_match_exact_linkage(tmp_path,field):
    root=_wp2c_fixture(tmp_path);rec=load_json(root/'record-1.json');parts=field.split('.');target=rec
    for p in parts[:-1]:target=target[p]
    leaf=parts[-1]
    if 'sha256' in leaf or 'digest' in leaf or parts[0]=='packet_sha256':value='0'*64
    elif field=='binding.relation_type':value='supports'
    elif field=='verification.result':value='supported'
    else:value='different'
    target[leaf]=value;_wp2c_write(root,'record-1.json',rec)
    r=_wp2c_run(root,_wp2c_repin(root))
    assert r['base_check']['status']=='LOCAL_BINDINGS_CONSISTENT'
    assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert _wp2c_has(r,'record_binding_mismatch')
    assert r['counts']['matching_records']==0
    _wp2c_limits(r)


@pytest.mark.parametrize('field,value',[('schema_version','other'),('candidate_status','active'),('authority_effect','release'),('release_authority_activation',True),('new_code','raise RuntimeError()')])
def test_wp2c_record_schema_is_closed(tmp_path,field,value):
    root=_wp2c_fixture(tmp_path);rec=load_json(root/'record-1.json');rec[field]=value
    _wp2c_write(root,'record-1.json',rec);r=_wp2c_run(root,_wp2c_repin(root))
    assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert r['records'][0]['result'] is None


@pytest.mark.parametrize('field',['verifier','subject','packet_sha256','binding','verification','record_id'])
def test_wp2c_missing_record_identity_is_not_accepted(tmp_path,field):
    root=_wp2c_fixture(tmp_path);rec=load_json(root/'record-1.json');del rec[field]
    _wp2c_write(root,'record-1.json',rec);r=_wp2c_run(root,_wp2c_repin(root))
    assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'


@pytest.mark.parametrize('label',['supported','contradicted','insufficient','unresolved'])
def test_wp2c_all_recorded_labels_remain_untrusted_declarations(tmp_path,label):
    root=_wp2c_fixture(tmp_path);rp=load_json(root/'relations.json');rec=load_json(root/'record-1.json')
    rp['relations'][0]['relation_verification']['result']=label
    rec['verification']['result']=label
    _wp2c_write(root,'relations.json',rp);_wp2c_write(root,'record-1.json',rec)
    r=_wp2c_run(root,_wp2c_repin(root,True))
    assert r['status']=='LOCAL_RECORD_BINDINGS_CONSISTENT'
    assert r['records'][0]['declared_result']==label
    _wp2c_limits(r)


@pytest.mark.parametrize('state',['not_requested','not_run','invalid_input','failed','not_applicable'])
def test_wp2c_record_cannot_complete_an_unperformed_relation(tmp_path,state):
    root=_wp2c_fixture(tmp_path);rp=load_json(root/'relations.json');rel=rp['relations'][0]
    rel['verifier_record_id']=None
    rel['relation_verification']={'status':state,'result':None,'reason':'not_executed'}
    _wp2c_write(root,'relations.json',rp)
    r=_wp2c_run(root,_wp2c_repin(root,True))
    assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert _wp2c_has(r,'record_without_completed_relation')
    assert r['records'][0]['result'] is None


def test_wp2c_manifest_record_id_cannot_be_substituted(tmp_path):
    root=_wp2c_fixture(tmp_path);rs=load_json(root/'record-set.json');rs['records'][0]['record_id']='substituted'
    _wp2c_write(root,'record-set.json',rs);r=_wp2c_run(root,_wp2c_pins(root))
    assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert 'manifest_record_id' in r['records'][0]['mismatched_fields']


def test_wp2c_completed_relation_requires_materialized_record_entry(tmp_path):
    root=_wp2c_fixture(tmp_path);rs=load_json(root/'record-set.json');rs['records']=[]
    _wp2c_write(root,'record-set.json',rs);r=_wp2c_run(root,_wp2c_pins(root))
    assert r['status']=='LOCAL_RECORD_BINDINGS_INCOMPLETE'
    assert _wp2c_has(r,'verifier_record_not_listed')
    assert r['counts']=={'completed_relations':1,'listed_records':0,'matching_records':0}


def test_wp2c_empty_expected_set_has_zero_matched_records_not_semantic_completion(tmp_path):
    root=_wp2c_fixture(tmp_path);rp=load_json(root/'relations.json');rp['relations']=[]
    rs=load_json(root/'record-set.json');rs['records']=[]
    _wp2c_write(root,'relations.json',rp);_wp2c_write(root,'record-set.json',rs)
    r=_wp2c_run(root,_wp2c_repin(root))
    assert r['status']=='LOCAL_RECORD_BINDINGS_CONSISTENT'
    assert r['counts']=={'completed_relations':0,'listed_records':0,'matching_records':0}
    assert r['records']==[]
    _wp2c_limits(r)


def test_wp2c_unreferenced_record_file_is_not_auto_discovered(tmp_path):
    root=_wp2c_fixture(tmp_path);rs=load_json(root/'record-set.json');rs['records']=[]
    _wp2c_write(root,'record-set.json',rs)
    r=_wp2c_run(root,_wp2c_pins(root));assert _wp2c_has(r,'verifier_record_not_listed')


def test_wp2c_one_record_id_cannot_cover_two_completed_relations(tmp_path):
    root=_wp2c_fixture(tmp_path);rp=load_json(root/'relations.json');other=deepcopy(rp['relations'][0]);other['binding_id']='second-binding'
    rp['relations'].append(other);_wp2c_write(root,'relations.json',rp)
    r=_wp2c_run(root,_wp2c_repin(root,True))
    assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert _wp2c_has(r,'verifier_record_id_reused')
    assert _wp2c_has(r,'verifier_record_not_listed')


def test_wp2c_invalid_wins_over_missing_record(tmp_path):
    root=_wp2c_fixture(tmp_path);rs=load_json(root/'record-set.json');extra=deepcopy(rs['records'][0])
    extra.update(record_id='extra-record',binding_id='unknown-binding',path='extra.json')
    rs['records'].append(extra);_wp2c_write(root,'record-set.json',rs);(root/'record-1.json').unlink()
    r=_wp2c_run(root,_wp2c_pins(root))
    assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert {x['severity'] for x in r['issues']}=={'invalid','incomplete'}


def test_wp2c_root_consistency_is_rerun_not_accepted_from_saved_json(tmp_path):
    root=_wp2c_fixture(tmp_path)
    (root/'saved-report.json').write_text('{"status":"LOCAL_BINDINGS_CONSISTENT"}')
    (root/'source.json').write_text('{"record":{"value":999}}')
    r=_wp2c_run(root)
    assert r['base_check']['status']=='LOCAL_BINDINGS_INVALID'
    assert r['records']==[] and r['counts']['matching_records'] is None


def test_wp2c_report_deterministic_and_inputs_unchanged(tmp_path):
    root=_wp2c_fixture(tmp_path);before={p.name:p.read_bytes() for p in root.iterdir()}
    a=_wp2c_run(root);b=_wp2c_run(root)
    assert a==b and before=={p.name:p.read_bytes() for p in root.iterdir()}
    m=_wp2c_module();base=m.load_binding_checker()
    br=base.verify_bundle(root,'input.json',WP2C_INPUT_PIN,'carriers.json',WP2C_CARRIERS_PIN,profile='wp2b-json-pointer-v1')
    assert a['base_check']['report_sha256']==m.digest(m.report_bytes(br))


def test_wp2c_shared_snapshot_not_reopened_after_base_check(tmp_path,monkeypatch):
    root=_wp2c_fixture(tmp_path);m=_wp2c_module();original=m.RecordReview.run_base
    def checked(self,reader,*args):
        ok=original(self,reader,*args)
        if ok:(root/'claims.json').write_text('changed after retained snapshot')
        return ok
    monkeypatch.setattr(m.RecordReview,'run_base',checked)
    r=_wp2c_run(root,module=m)
    assert r['status']=='LOCAL_RECORD_BINDINGS_CONSISTENT'
    # The report describes retained pinned bytes, not a claim about later disk state.
    _wp2c_limits(r)


@pytest.mark.parametrize('kind',['symlink','hardlink','directory','fifo'])
def test_wp2c_record_files_keep_existing_safe_reader_boundary(tmp_path,kind):
    root=_wp2c_fixture(tmp_path);p=root/'record-1.json';raw=p.read_bytes();p.unlink()
    if kind=='directory':p.mkdir()
    elif kind=='fifo':_wp2c_os.mkfifo(p)
    else:
        target=tmp_path/'external';target.write_bytes(raw)
        if kind=='symlink':p.symlink_to(target)
        else:_wp2c_os.link(target,p)
    r=_wp2c_run(root);assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert r['counts']['matching_records']==0


@pytest.mark.parametrize('content',[b'{"a":1,"a":2}',b'[]',b'{broken',b'{"x":NaN}',b'{"x":"\\ud800"}',b'\xff',b'{} trailing'])
@pytest.mark.parametrize('filename',['record-set.json','record-1.json'])
def test_wp2c_strict_record_json_rejects_ambiguous_or_malformed_bytes(tmp_path,content,filename):
    root=_wp2c_fixture(tmp_path);(root/filename).write_bytes(content)
    if filename=='record-1.json':
        rs=load_json(root/'record-set.json');rs['records'][0]['sha256']=_wp2c_hash(root/filename);_wp2c_write(root,'record-set.json',rs)
    r=_wp2c_run(root,_wp2c_pins(root));assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert r['counts']['matching_records'] in (0,None)


def test_wp2c_record_digest_checked_before_json_interpretation(tmp_path):
    root=_wp2c_fixture(tmp_path);(root/'record-1.json').write_text('not json')
    r=_wp2c_run(root);assert _wp2c_has(r,'record_digest_mismatch')
    assert r['records'][0]['result']=='mismatch'


@pytest.mark.parametrize('key,value',[('requested_checks_complete',True),('accepted_as_semantic_support',True),('release_authority_activation',True),('authority_effect','release'),('candidate_status','active')])
def test_wp2c_report_cannot_be_promoted(key,value):
    r=_wp2c_run();r[key]=value;m=_wp2c_module();base=m.load_binding_checker()
    with pytest.raises(base.BindingError):m.RecordSchemas(base).validate('report',r)


@pytest.mark.parametrize('key',_wp2c_module().UNPERFORMED)
def test_wp2c_unperformed_checks_cannot_carry_results(key):
    r=_wp2c_run();r['unperformed_checks'][key]={'status':'completed','result':'verified','reason':None}
    m=_wp2c_module();base=m.load_binding_checker()
    with pytest.raises(base.BindingError):m.RecordSchemas(base).validate('report',r)


@pytest.mark.parametrize('mutation',['base_missing','base_invalid','issue','row_null','row_semantic','record_stage','unknown_field'])
def test_wp2c_schema_rejects_false_consistent_reports(mutation):
    r=_wp2c_run()
    if mutation=='base_missing':r['base_check']['status']=None
    elif mutation=='base_invalid':r['base_check']['status']='LOCAL_BINDINGS_INVALID'
    elif mutation=='issue':r['issues']=[{'severity':'invalid','code':'mismatch','object_id':'test'}]
    elif mutation=='row_null':r['records'][0]['result']=None
    elif mutation=='row_semantic':r['records'][0]['accepted_as_semantic_support']=True
    elif mutation=='record_stage':r['record_check']={'status':'not_run','result':None,'reason':'not_done'}
    else:r['release_decision']='PASS'
    m=_wp2c_module();base=m.load_binding_checker()
    with pytest.raises(base.BindingError):m.RecordSchemas(base).validate('report',r)


def test_wp2c_native_wp2a_mode_also_supports_record_binding(tmp_path):
    root=tmp_path/'wp2a';_wp2c_shutil.copytree(WP2_DEMO,root)
    rs=load_json(WP2C_DEMO/'record-set.json');rs.update(binding_profile='wp2a',records=[])
    _wp2c_write(root,'record-set.json',rs)
    r=_wp2c_run(root,_wp2c_repin(root),profile='wp2a')
    assert r['status']=='LOCAL_RECORD_BINDINGS_CONSISTENT'
    assert r['counts']['matching_records']==0
    assert r['implementation']['json_pointer_module_sha256'] is None
    _wp2c_limits(r)


def test_wp2c_missing_base_bytes_prevent_record_stage(tmp_path):
    root=_wp2c_fixture(tmp_path);(root/'source.json').unlink()
    r=_wp2c_run(root)
    assert r['base_check']['status']=='LOCAL_BINDINGS_INCOMPLETE'
    assert r['record_check']['result'] is None and r['records']==[]


def test_wp2c_record_count_budget(tmp_path,monkeypatch):
    root=_wp2c_fixture(tmp_path);m=_wp2c_module();base=m.load_binding_checker()
    monkeypatch.setattr(base,'MAX_ITEMS',0);monkeypatch.setattr(m,'load_binding_checker',lambda:base)
    # Schema loading itself is bounded under this deliberately impossible limit.
    with pytest.raises(base.BindingError):_wp2c_run(root,module=m)


def test_wp2c_record_byte_and_total_budgets_are_shared(tmp_path,monkeypatch):
    root=_wp2c_fixture(tmp_path);m=_wp2c_module();base=m.load_binding_checker()
    size=sum(p.stat().st_size for p in root.iterdir() if p.is_file())
    monkeypatch.setattr(base,'MAX_TOTAL_BYTES',size-1);monkeypatch.setattr(m,'load_binding_checker',lambda:base)
    r=_wp2c_run(root,module=m)
    assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert _wp2c_has(r,'bundle_limit_exceeded')


def test_wp2c_schema_reference_resolution_is_not_enabled(tmp_path,monkeypatch):
    m=_wp2c_module();base=m.load_binding_checker();install=tmp_path/'install'
    _wp2c_shutil.copytree(ROOT/'schemas',install/'schemas')
    path=install/'schemas'/m.SCHEMAS['record'];schema=load_json(path);schema['$ref']='https://invalid.example/schema'
    path.write_text(json.dumps(schema));monkeypatch.setattr(m,'ROOT',install)
    with pytest.raises(base.BindingError,match='schema_reference_not_allowed'):m.RecordSchemas(base)


def test_wp2c_fixed_checker_import_does_not_write_bytecode(tmp_path,monkeypatch):
    m=_wp2c_module();install=tmp_path/'install';(install/'tools').mkdir(parents=True)
    _wp2c_shutil.copyfile(ROOT/'tools/check_anchor_integrity_bindings_v0_1.py',install/'tools/check_anchor_integrity_bindings_v0_1.py')
    monkeypatch.setattr(m,'ROOT',install);before=_wp2c_sys.dont_write_bytecode;m.load_binding_checker()
    assert _wp2c_sys.dont_write_bytecode==before
    assert not (install/'tools/__pycache__').exists()


def test_wp2c_expected_verifier_is_pinned_but_not_authenticated(tmp_path):
    root=_wp2c_fixture(tmp_path);rec=load_json(root/'record-1.json');rs=load_json(root/'record-set.json')
    rec['verifier']['verifier_id']='self-declared-verifier'
    rs['records'][0]['expected_verifier']=deepcopy(rec['verifier'])
    _wp2c_write(root,'record-1.json',rec);_wp2c_write(root,'record-set.json',rs)
    r=_wp2c_run(root,_wp2c_repin(root));assert r['status']=='LOCAL_RECORD_BINDINGS_CONSISTENT'
    _wp2c_limits(r)


def _wp2c_command(root,pins=None):
    pins=pins or (WP2C_INPUT_PIN,WP2C_CARRIERS_PIN,WP2C_SET_PIN)
    return [_wp2c_sys.executable,str(WP2C_TOOL),'--bundle-root',str(root),'--input','input.json','--expected-input-sha256',pins[0],'--carriers','carriers.json','--expected-carriers-sha256',pins[1],'--record-set','record-set.json','--expected-record-set-sha256',pins[2],'--binding-profile','wp2b-json-pointer-v1']


@pytest.mark.parametrize('case,exit_code',[('positive',0),('wrong_record',1),('missing_record',2)])
def test_wp2c_cli_exit_codes_and_stdout(tmp_path,case,exit_code):
    root=_wp2c_fixture(tmp_path)
    if case=='wrong_record':(root/'record-1.json').write_bytes(b'changed')
    if case=='missing_record':(root/'record-1.json').unlink()
    result=_wp2c_subprocess.run(_wp2c_command(root),capture_output=True,timeout=45)
    assert result.returncode==exit_code,result.stderr
    r=json.loads(result.stdout);_wp2c_limits(r)
    assert not result.stderr


@pytest.mark.parametrize('option',['--expected-input-sha256','--expected-carriers-sha256','--expected-record-set-sha256','--binding-profile'])
def test_wp2c_cli_requires_all_explicit_root_expectations(option):
    cmd=_wp2c_command(WP2C_DEMO);i=cmd.index(option);del cmd[i:i+2]
    result=_wp2c_subprocess.run(cmd,capture_output=True,timeout=45)
    assert result.returncode==2 and not result.stdout


def test_wp2c_existing_anchor_registration_unchanged():
    for name in ('ci/tools-tests.list','ci/pytest-tests.list'):
        assert _manifest_entries(ROOT/name).count(TEST_PATH)==1


def test_wp2c_new_schemas_validate_under_draft_2020_12():
    m=_wp2c_module();base=m.load_binding_checker();schemas=m.RecordSchemas(base)
    for name in m.SCHEMAS.values():
        jsonschema.Draft202012Validator.check_schema(load_json(ROOT/'schemas'/name))
    schemas.validate('set',load_json(WP2C_DEMO/'record-set.json'))
    schemas.validate('record',load_json(WP2C_DEMO/'record-1.json'))


def test_wp2c_documentation_retains_non_authentication_boundary():
    text=(ROOT/'docs/ANCHOR_INTEGRITY_v0_1_WP2C_VERIFIER_RECORDS.md').read_text()
    for value in ('verifier_execution_attestation','not_run','LOCAL_RECORD_BINDINGS_CONSISTENT','No verifier is executed','one retained','zero'):
        assert value in text


def test_wp2c_two_distinct_records_cover_two_completed_relations(tmp_path):
    root=_wp2c_fixture(tmp_path);rp=load_json(root/'relations.json');rs=load_json(root/'record-set.json')
    rel=deepcopy(rp['relations'][0]);rel.update(binding_id='binding-2',verifier_record_id='synthetic-record-2')
    rp['relations'].append(rel);_wp2c_write(root,'relations.json',rp)
    rec=load_json(root/'record-1.json');rec['record_id']='synthetic-record-2';rec['binding']['binding_id']='binding-2'
    _wp2c_write(root,'record-2.json',rec)
    entry=deepcopy(rs['records'][0]);entry.update(record_id='synthetic-record-2',binding_id='binding-2',path='record-2.json')
    rs['records'].append(entry);_wp2c_write(root,'record-set.json',rs)
    r=_wp2c_run(root,_wp2c_repin(root,True))
    assert r['status']=='LOCAL_RECORD_BINDINGS_CONSISTENT'
    assert r['counts']=={'completed_relations':2,'listed_records':2,'matching_records':2}
    assert [x['binding_id'] for x in r['records']]==['binding-1','binding-2']
    _wp2c_limits(r)


def test_wp2c_record_manifest_list_limit_is_checked_before_file_open(tmp_path,monkeypatch):
    root=_wp2c_fixture(tmp_path);rs=load_json(root/'record-set.json');template=rs['records'][0]
    rs['records']=[dict(template,record_id=f'record-{i}',binding_id=f'binding-{i}',path=f'record-{i}.json') for i in range(33)]
    _wp2c_write(root,'record-set.json',rs)
    m=_wp2c_module();base=m.load_binding_checker();monkeypatch.setattr(base,'MAX_ITEMS',32)
    monkeypatch.setattr(m,'load_binding_checker',lambda:base)
    r=_wp2c_run(root,_wp2c_pins(root),module=m)
    assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert _wp2c_has(r,'item_limit_exceeded')
    assert r['records']==[]


def test_wp2c_record_file_size_limit_is_checked_before_interpretation(tmp_path):
    root=_wp2c_fixture(tmp_path)
    with (root/'record-1.json').open('wb') as f:f.truncate(8*1024*1024+1)
    r=_wp2c_run(root)
    assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert _wp2c_has(r,'file_limit_exceeded')
    assert r['records'][0]['observed_sha256'] is None


def test_wp2c_changed_record_during_read_is_rejected(tmp_path,monkeypatch):
    root=_wp2c_fixture(tmp_path);m=_wp2c_module();base=m.load_binding_checker()
    original=base.os.read;target=(root/'record-1.json').stat().st_ino;changed=[]
    def mutate(fd,size):
        data=original(fd,size)
        if base.os.fstat(fd).st_ino==target and not changed:
            with (root/'record-1.json').open('ab') as stream:stream.write(b' ')
            changed.append(True)
        return data
    monkeypatch.setattr(base.os,'read',mutate);monkeypatch.setattr(m,'load_binding_checker',lambda:base)
    r=_wp2c_run(root,module=m)
    assert changed and r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert _wp2c_has(r,'carrier_changed_during_read')


def test_wp2c_cli_does_not_create_output_files_or_mutate_inputs(tmp_path):
    root=_wp2c_fixture(tmp_path);before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result=_wp2c_subprocess.run(_wp2c_command(root),capture_output=True,timeout=45)
    assert result.returncode==0,result.stderr
    after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert before==after


def test_wp2c_cli_has_no_saved_approval_or_output_override():
    cmd=_wp2c_command(WP2C_DEMO)+['--saved-base-report','saved.json','--output','status.json']
    result=_wp2c_subprocess.run(cmd,capture_output=True,timeout=45)
    assert result.returncode==2 and not result.stdout


def test_wp2c_missing_installed_schema_cli_returns_no_success_json(tmp_path):
    install=tmp_path/'install';(install/'tools').mkdir(parents=True)
    for name in ('check_anchor_integrity_verifier_records_v0_1.py','check_anchor_integrity_bindings_v0_1.py'):
        _wp2c_shutil.copyfile(ROOT/'tools'/name,install/'tools'/name)
    cmd=_wp2c_command(WP2C_DEMO);cmd[1]=str(install/'tools'/WP2C_TOOL.name)
    result=_wp2c_subprocess.run(cmd,capture_output=True,timeout=45)
    assert result.returncode==2 and not result.stdout
    assert b'Anchor record checker error' in result.stderr


def test_wp2c_manifest_cannot_select_code_or_schema_from_artifact(tmp_path):
    root=_wp2c_fixture(tmp_path);rs=load_json(root/'record-set.json')
    rs['verifier_plugin']='record-1.json';rs['schema_path']='record-1.json'
    _wp2c_write(root,'record-set.json',rs);r=_wp2c_run(root,_wp2c_pins(root))
    assert r['status']=='LOCAL_RECORD_BINDINGS_INVALID'
    assert r['base_check']['status'] is None


# WP2D: declared typed dependency cycles, not independent-anchor admission.
WP2D_TOOL = ROOT / 'tools/check_anchor_integrity_dependency_cycles_v0_1.py'
WP2D_DEMO = ROOT / 'examples/anchor_integrity_v0_1/wp2d_dependency_cycles'
WP2D_PINS = (
    '1e3a63612f274b9c3e3f518f0e9528386806403783d10fbd395b3348d8dc2574',
    'ce21a2e7fbdd7f1dfbb3cfdcadd286329684be0bc2ff0a97f9d9953cc4474935',
    '6719379a23cde24a122f8f82c81bb2245ac93a7e49de873295a18fa8532bbfa9',
)


def _wp2d_module():
    spec = _wp2c_importlib.spec_from_file_location('wp2d_test_checker', WP2D_TOOL)
    module = _wp2c_importlib.module_from_spec(spec)
    previous = _wp2c_sys.dont_write_bytecode
    _wp2c_sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        _wp2c_sys.dont_write_bytecode = previous
    return module


def _wp2d_fixture(tmp_path):
    root = tmp_path / 'cycles'
    _wp2c_shutil.copytree(WP2D_DEMO, root)
    return root


def _wp2d_refresh(root, bind_graph_packets=True, sync_records=True):
    """Explicit synthetic-fixture rebinding; optionally leave graph assertions stale."""
    rel = load_json(root / 'relations.json')
    for key, name in [('claim_packet_binding', 'claims.json'), ('evidence_packet_binding', 'evidence.json')]:
        rel[key]['sha256'] = _wp2c_hash(root / name)
    _wp2c_write(root, 'relations.json', rel)
    if bind_graph_packets:
        graph = load_json(root / 'graph.json')
        graph['packet_sha256'] = {key:_wp2c_hash(root/name) for key,name in
                                 [('claims','claims.json'),('evidence','evidence.json'),('relations','relations.json')]}
        _wp2c_write(root, 'graph.json', graph)
    inp = load_json(root / 'input.json')
    if inp['paradox_graph_binding'] is not None:
        inp['paradox_graph_binding']['sha256'] = _wp2c_hash(root / inp['paradox_graph_binding']['path'])
    _wp2c_write(root, 'input.json', inp)
    if sync_records:
        relations = {r['binding_id']:r for r in rel['relations']}
        rs = load_json(root/'record-set.json')
        for entry in rs['records']:
            record = load_json(root/entry['path'])
            relation = relations[entry['binding_id']]
            record['binding']['relation_type'] = relation['relation_type']
            record['verification'] = relation['relation_verification']
            _wp2c_write(root, entry['path'], record)
    return _wp2c_repin(root, sync_record_roots=True)


def _wp2d_run(root=WP2D_DEMO, pins=None, module=None, profile='typed-dependencies-v1', binding='wp2b-json-pointer-v1'):
    if pins is None:
        pins = WP2D_PINS
    m = module or _wp2d_module()
    return m.verify_cycles(root, 'input.json', pins[0], 'carriers.json', pins[1],
                           'record-set.json', pins[2], binding_profile=binding, cycle_profile=profile)


def _wp2d_limits(report):
    assert report['candidate_status'] == 'diagnostic_only'
    assert report['authority_effect'] == 'none'
    for key in ['release_authority_activation','requested_checks_complete',
                'accepted_as_semantic_support','whole_response_cycle_freedom_established']:
        assert report[key] is False
    assert report['cycle_anchor_classification']['status'] == 'not_run'
    assert report['cycle_anchor_classification']['result'] is None
    for stage in report['unperformed_checks'].values():
        assert stage['status'] == 'not_run' and stage['result'] is None


def _wp2d_witnesses(report):
    edges = {e['edge_key']:e for e in report['edges']}
    for component in report['cyclic_components']:
        nodes = component['witness']['nodes']
        keys = component['witness']['edge_keys']
        assert nodes[0] == nodes[-1]
        assert len(nodes) == len(keys) + 1
        assert len(set(nodes[:-1])) == len(nodes) - 1
        assert set(nodes).issubset(component['nodes'])
        for source, target, key in zip(nodes, nodes[1:], keys):
            assert (edges[key]['from'], edges[key]['to']) == (source, target)
            assert key in component['internal_edge_keys']


def _wp2d_edge(edge_id='edge-1', edge_type='claim_depends_on_claim', source='claim-1', target='claim-2', kind='claim'):
    return {'edge_id':edge_id,'type':edge_type,'from':{'kind':kind,'object_id':source},
            'to':{'kind':'claim','object_id':target}}


def test_wp2d_synthetic_cycle_has_exact_witness_without_semantic_promotion():
    report = _wp2d_run()
    assert report['status'] == 'LOCAL_DEPENDENCY_GRAPH_ANALYZED'
    assert report['cycle_detection']['result'] == 'cycle_detected'
    assert report['counts'] == {'nodes':3,'claims':2,'evidence_items':1,'explicit_edges':1,
                                'derived_relation_edges':1,'ignored_relations':0,'edges':2,
                                'components':2,'cyclic_components':1}
    assert report['cyclic_components'][0]['witness'] == {
        'nodes':['claim:claim-1','evidence:evidence-1','claim:claim-1'],
        'edge_keys':['relation:binding-1','graph:evidence-return']}
    _wp2d_witnesses(report)
    _wp2d_limits(report)


@pytest.mark.parametrize('edge_type',['supported_by_claim','derived_from_claim','claim_depends_on_claim','evidence_depends_on_claim'])
def test_wp2d_reserved_types_have_explicit_direction(tmp_path, edge_type):
    root=_wp2d_fixture(tmp_path);graph=load_json(root/'graph.json')
    evidence=edge_type=='evidence_depends_on_claim'
    graph['dependency_edges']=[_wp2d_edge(edge_type=edge_type,source='evidence-1' if evidence else 'claim-1',target='claim-1',kind='evidence' if evidence else 'claim')]
    _wp2c_write(root,'graph.json',graph)
    report=_wp2d_run(root,_wp2d_refresh(root))
    assert report['cycle_detection']['result']=='cycle_detected'
    _wp2d_witnesses(report);_wp2d_limits(report)


@pytest.mark.parametrize('relation_type,expected',[('supports',1),('derived_from',1),('references',0),('contextualizes',0),('contradicts',0)])
def test_wp2d_only_dependency_relations_become_claim_evidence_edges(tmp_path,relation_type,expected):
    root=_wp2d_fixture(tmp_path);rel=load_json(root/'relations.json')
    rel['relations'][0]['relation_type']=relation_type;_wp2c_write(root,'relations.json',rel)
    report=_wp2d_run(root,_wp2d_refresh(root))
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_ANALYZED'
    assert report['counts']['derived_relation_edges']==expected
    assert report['counts']['ignored_relations']==1-expected
    assert report['cycle_detection']['result']==('cycle_detected' if expected else 'no_cycle_detected_in_declared_graph')
    _wp2d_limits(report)


@pytest.mark.parametrize('verdict',['supported','contradicted','insufficient','unresolved'])
def test_wp2d_recorded_verdict_does_not_erase_declared_dependency_or_authenticate_it(tmp_path,verdict):
    root=_wp2d_fixture(tmp_path);rel=load_json(root/'relations.json')
    rel['relations'][0]['relation_verification']['result']=verdict;_wp2c_write(root,'relations.json',rel)
    report=_wp2d_run(root,_wp2d_refresh(root))
    assert report['cycle_detection']['result']=='cycle_detected';_wp2d_limits(report)


@pytest.mark.parametrize('state',['not_requested','not_run','invalid_input','failed','not_applicable'])
def test_wp2d_uncompleted_relation_still_projects_its_declared_dependency(tmp_path,state):
    root=_wp2d_fixture(tmp_path);rel=load_json(root/'relations.json')
    rel['relations'][0].update(relation_verification={'status':state,'result':None,'reason':'synthetic_unperformed'},verifier_record_id=None)
    _wp2c_write(root,'relations.json',rel);rs=load_json(root/'record-set.json');rs['records']=[];_wp2c_write(root,'record-set.json',rs)
    report=_wp2d_run(root,_wp2d_refresh(root))
    assert report['cycle_detection']['result']=='cycle_detected';_wp2d_limits(report)


@pytest.mark.parametrize('mode',['acyclic','claim_self_loop','two_components','three_nodes','parallel_types'])
def test_wp2d_topology_cases(tmp_path,mode):
    root=_wp2d_fixture(tmp_path);graph=load_json(root/'graph.json')
    if mode=='acyclic':graph['dependency_edges']=[]
    elif mode=='claim_self_loop':graph['dependency_edges']=[_wp2d_edge(source='claim-2',target='claim-2')]
    elif mode=='two_components':graph['dependency_edges'].append(_wp2d_edge(source='claim-2',target='claim-2'))
    elif mode=='three_nodes':
        graph['dependency_edges'][0]['to']['object_id']='claim-2'
        graph['dependency_edges'].append(_wp2d_edge(source='claim-2',target='claim-1'))
    else:
        graph['dependency_edges']=[_wp2d_edge('a',source='claim-2',target='claim-2'),_wp2d_edge('b',edge_type='supported_by_claim',source='claim-2',target='claim-2')]
    _wp2c_write(root,'graph.json',graph);report=_wp2d_run(root,_wp2d_refresh(root))
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_ANALYZED'
    assert report['counts']['cyclic_components']==(0 if mode=='acyclic' else 2 if mode=='two_components' else 1)
    if mode=='three_nodes':assert len(report['cyclic_components'][0]['nodes'])==3
    _wp2d_witnesses(report);_wp2d_limits(report)


@pytest.mark.parametrize('mutation',['subject','run','claims_digest','evidence_digest','relations_digest','claim_set'])
def test_wp2d_rehashed_graph_must_match_retained_packet_identities(tmp_path,mutation):
    root=_wp2d_fixture(tmp_path);graph=load_json(root/'graph.json')
    if mutation=='subject':graph['subject']['subject_id']='other'
    elif mutation=='run':graph['subject']['run_id']='other'
    elif mutation=='claim_set':graph['claim_set_id']='other'
    else:graph['packet_sha256'][mutation.split('_')[0]]='0'*64
    _wp2c_write(root,'graph.json',graph);report=_wp2d_run(root,_wp2d_refresh(root,bind_graph_packets=False))
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert report['cycle_detection']['result'] is None
    assert report['record_check']['status']=='LOCAL_RECORD_BINDINGS_CONSISTENT'


@pytest.mark.parametrize('mutation',['unknown_type','wrong_from_kind','wrong_to_kind','missing_edge_id','duplicate_id','duplicate_tuple','unknown_claim','unknown_evidence','cross_kind_id','extra_anchor','schema','profile','coverage','authority','candidate','activation'])
def test_wp2d_graph_contract_rejects_ambiguous_or_promoted_inputs(tmp_path,mutation):
    root=_wp2d_fixture(tmp_path);graph=load_json(root/'graph.json');edge=graph['dependency_edges'][0]
    if mutation=='unknown_type':edge['type']='related_to'
    elif mutation=='wrong_from_kind':edge['from']['kind']='claim'
    elif mutation=='wrong_to_kind':edge['to']['kind']='evidence'
    elif mutation=='missing_edge_id':del edge['edge_id']
    elif mutation=='duplicate_id':graph['dependency_edges'].append(deepcopy(edge))
    elif mutation=='duplicate_tuple':second=deepcopy(edge);second['edge_id']='other';graph['dependency_edges'].append(second)
    elif mutation=='unknown_claim':edge['to']['object_id']='missing'
    elif mutation=='unknown_evidence':edge['from']['object_id']='missing'
    elif mutation=='cross_kind_id':edge['from']['object_id']='claim-1'
    elif mutation=='extra_anchor':graph['independent_anchors']=['claim-1']
    elif mutation=='schema':graph['schema_version']='unknown'
    elif mutation=='profile':graph['projection_profile']='unknown'
    elif mutation=='coverage':graph['coverage']='complete'
    elif mutation=='authority':graph['authority_effect']='release'
    elif mutation=='candidate':graph['candidate_status']='active'
    else:graph['release_authority_activation']=True
    _wp2c_write(root,'graph.json',graph);report=_wp2d_run(root,_wp2d_refresh(root))
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert report['cycle_detection']['status']=='not_run'


@pytest.mark.parametrize('name',['graph.json','record-1.json','source.json','claims.json','record-set.json'])
def test_wp2d_missing_required_bytes_prevent_cycle_result(tmp_path,name):
    root=_wp2d_fixture(tmp_path);(root/name).unlink();report=_wp2d_run(root)
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INCOMPLETE'
    assert report['cycle_detection']['result'] is None
    assert report['nodes']==[]


@pytest.mark.parametrize('content',[b'{broken',b'{"x":1,"x":2}',b'[]',b'{"x":NaN}',b'\xff',b'{} trailing'])
def test_wp2d_rehashed_malformed_graph_never_yields_measurement(tmp_path,content):
    root=_wp2d_fixture(tmp_path);(root/'graph.json').write_bytes(content)
    report=_wp2d_run(root,_wp2d_refresh(root,bind_graph_packets=False))
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert report['cycle_detection']['result'] is None


def test_wp2d_absent_graph_binding_is_incomplete_not_acyclic(tmp_path):
    root=_wp2d_fixture(tmp_path);inp=load_json(root/'input.json');inp['paradox_graph_binding']=None
    _wp2c_write(root,'input.json',inp);report=_wp2d_run(root,_wp2d_refresh(root))
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INCOMPLETE'
    assert report['record_check']['status']=='LOCAL_RECORD_BINDINGS_CONSISTENT'
    assert report['cycle_detection']['result'] is None


def test_wp2d_other_graph_schema_is_not_silently_reinterpreted(tmp_path):
    root=_wp2d_fixture(tmp_path);inp=load_json(root/'input.json');graph=load_json(root/'graph.json')
    inp['paradox_graph_binding']['schema_version']='another_graph_v1';graph['schema_version']='another_graph_v1'
    _wp2c_write(root,'input.json',inp);_wp2c_write(root,'graph.json',graph)
    report=_wp2d_run(root,_wp2d_refresh(root))
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert any(x['code']=='unsupported_dependency_graph_schema' for x in report['issues'])


@pytest.mark.parametrize('which',[0,1,2])
@pytest.mark.parametrize('bad',['0'*64,'bad',None])
def test_wp2d_external_expectations_are_required(tmp_path,which,bad):
    pins=list(WP2D_PINS);pins[which]=bad;report=_wp2d_run(_wp2d_fixture(tmp_path),pins)
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert report['cycle_detection']['result'] is None


@pytest.mark.parametrize('name',['input.json','carriers.json','graph.json','record-1.json','source.json'])
def test_wp2d_changed_bytes_are_not_concealed_by_old_hashes(tmp_path,name):
    root=_wp2d_fixture(tmp_path);p=root/name;p.write_bytes(p.read_bytes()+b' ')
    report=_wp2d_run(root)
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert report['cycle_detection']['result'] is None


def test_wp2d_invalid_precedes_missing(tmp_path):
    root=_wp2d_fixture(tmp_path);(root/'record-1.json').unlink();p=root/'source.json';p.write_bytes(p.read_bytes()+b' ')
    report=_wp2d_run(root)
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert report['cycle_detection']['result'] is None


@pytest.mark.parametrize('kind',['symlink','hardlink','directory','fifo'])
def test_wp2d_graph_uses_existing_safe_reader_boundary(tmp_path,kind):
    root=_wp2d_fixture(tmp_path);p=root/'graph.json';data=p.read_bytes();p.unlink()
    if kind in ('symlink','hardlink'):
        other=root/'other.json';other.write_bytes(data)
        if kind=='symlink':p.symlink_to(other)
        else:_wp2c_os.link(other,p)
    elif kind=='directory':p.mkdir()
    else:_wp2c_os.mkfifo(p)
    report=_wp2d_run(root)
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert report['cycle_detection']['result'] is None


@pytest.mark.parametrize('alias',['claims.json','source.json','record-1.json','record-set.json','carriers.json','input.json'])
def test_wp2d_graph_cannot_alias_another_role(tmp_path,alias):
    root=_wp2d_fixture(tmp_path);inp=load_json(root/'input.json');inp['paradox_graph_binding']['path']=alias
    _wp2c_write(root,'input.json',inp)
    # Binding an alias must fail even when callers re-pin the reachable roots.
    report=_wp2d_run(root,_wp2d_refresh(root))
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert report['cycle_detection']['result'] is None


def test_wp2d_graph_uses_retained_bytes_after_record_check(tmp_path,monkeypatch):
    root=_wp2d_fixture(tmp_path);m=_wp2d_module();records=m.load_record_checker()
    original=records.RecordReview.records
    def changed(self,reader,record_set,input_path):
        original(self,reader,record_set,input_path)
        (root/'graph.json').write_bytes(b'{"changed_after_read":true}')
    monkeypatch.setattr(records.RecordReview,'records',changed)
    monkeypatch.setattr(m,'load_record_checker',lambda:records)
    report=_wp2d_run(root,module=m)
    assert report['cycle_detection']['result']=='cycle_detected'
    assert report['graph_binding']['observed_sha256']!=_wp2c_hash(root/'graph.json')
    _wp2d_limits(report)


@pytest.mark.parametrize('field,limit',[('MAX_GRAPH_NODES',2),('MAX_GRAPH_EDGES',1)])
def test_wp2d_projection_budgets_reject_before_result(tmp_path,monkeypatch,field,limit):
    m=_wp2d_module();monkeypatch.setattr(m,field,limit)
    report=_wp2d_run(_wp2d_fixture(tmp_path),module=m)
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert report['cycle_detection']['result'] is None


def test_wp2d_input_edge_budget_is_bounded(tmp_path):
    root=_wp2d_fixture(tmp_path);g=load_json(root/'graph.json')
    g['dependency_edges']=[_wp2d_edge(str(i)) for i in range(4097)]
    _wp2c_write(root,'graph.json',g);report=_wp2d_run(root,_wp2d_refresh(root))
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert report['cycle_detection']['result'] is None


@pytest.mark.parametrize('field,value',[('authority_effect','release'),('candidate_status','active'),('release_authority_activation',True),('requested_checks_complete',True),('accepted_as_semantic_support',True),('whole_response_cycle_freedom_established',True)])
def test_wp2d_report_cannot_promote_structural_observation(field,value):
    m=_wp2d_module();r=_wp2d_run(module=m);r[field]=value;records=m.load_record_checker();base=records.load_binding_checker()
    with pytest.raises(base.BindingError):m.CycleSchemas(base).validate('report',r)


@pytest.mark.parametrize('key',_wp2d_module().UNPERFORMED)
def test_wp2d_unperformed_checks_reject_nonnull_results(key):
    m=_wp2d_module();r=_wp2d_run(module=m);r['unperformed_checks'][key].update(status='completed',result='verified')
    records=m.load_record_checker();base=records.load_binding_checker()
    with pytest.raises(base.BindingError):m.CycleSchemas(base).validate('report',r)


@pytest.mark.parametrize('result',['low','medium','high','anchored_cycle_observed','unanchored_cycle_detected','no_unanchored_cycle_detected'])
def test_wp2d_no_anchor_or_risk_classification_is_fabricated(result):
    m=_wp2d_module();r=_wp2d_run(module=m);r['cycle_anchor_classification'].update(status='completed',result=result)
    base=m.load_record_checker().load_binding_checker()
    with pytest.raises(base.BindingError):m.CycleSchemas(base).validate('report',r)


@pytest.mark.parametrize('mutation',['erase_cycles','erase_result','false_acyclic','invalid_with_measurement','base_not_checked','issues_with_success','null_count'])
def test_wp2d_report_schema_rejects_false_completed_shapes(mutation):
    m=_wp2d_module();r=_wp2d_run(module=m)
    if mutation=='erase_cycles':r['cyclic_components']=[]
    elif mutation=='erase_result':r['cycle_detection']['result']=None
    elif mutation=='false_acyclic':r['cycle_detection']['result']='no_cycle_detected_in_declared_graph'
    elif mutation=='invalid_with_measurement':r['status']='LOCAL_DEPENDENCY_GRAPH_INVALID'
    elif mutation=='base_not_checked':r['record_check']['status']=None
    elif mutation=='issues_with_success':r['issues'].append({'code':'x','object_id':'x','severity':'incomplete'})
    else:r['counts']['edges']=None
    base=m.load_record_checker().load_binding_checker()
    with pytest.raises(base.BindingError):m.CycleSchemas(base).validate('report',r)


def _wp2d_simple_edges(pairs):
    return [{'edge_key':'graph:e'+str(i),'from':a,'to':b} for i,(a,b) in enumerate(pairs)]


def _wp2d_independent_components(nodes,pairs):
    reach={(a,b) for a,b in pairs}
    for middle in nodes:
        for source in nodes:
            for target in nodes:
                if (source,middle) in reach and (middle,target) in reach:
                    reach.add((source,target))
    groups=set()
    for source in nodes:
        groups.add(tuple(sorted(n for n in nodes if n==source or ((source,n) in reach and (n,source) in reach))))
    cyclic=sorted(g for g in groups if len(g)>1 or (g[0],g[0]) in reach)
    return len(groups),cyclic


def test_wp2d_algorithm_matches_all_512_directed_three_node_graphs():
    m=_wp2d_module();nodes=['a','b','c'];possible=[(a,b) for a in nodes for b in nodes]
    for mask in range(1<<len(possible)):
        pairs=[pair for i,pair in enumerate(possible) if mask & (1<<i)]
        edges=_wp2d_simple_edges(pairs);result=m.analyze_projection(nodes,edges)
        count,cycles=_wp2d_independent_components(nodes,pairs)
        assert result['component_count']==count,(mask,result)
        assert [tuple(c['nodes']) for c in result['cyclic_components']]==cycles,(mask,result)
        _wp2d_witnesses({'edges':edges,'cyclic_components':result['cyclic_components']})


def test_wp2d_algorithm_matches_seeded_larger_graphs_and_permutations():
    import random
    rng=random.Random(2983);m=_wp2d_module();nodes=[str(i) for i in range(8)]
    for _ in range(64):
        pairs=[(a,b) for a in nodes for b in nodes if rng.randrange(6)==0]
        edges=_wp2d_simple_edges(pairs);a=m.analyze_projection(nodes,edges)
        count,cycles=_wp2d_independent_components(nodes,pairs)
        assert a['component_count']==count
        assert [tuple(c['nodes']) for c in a['cyclic_components']]==cycles
        rng.shuffle(edges);order=nodes[:];rng.shuffle(order)
        assert m.analyze_projection(order,edges)==a
        _wp2d_witnesses({'edges':edges,'cyclic_components':a['cyclic_components']})


@pytest.mark.parametrize('cycle',[False,True])
def test_wp2d_long_graph_is_not_python_recursion_limited(cycle):
    m=_wp2d_module();nodes=['n'+str(i) for i in range(5000)]
    pairs=list(zip(nodes,nodes[1:]))
    if cycle:pairs.append((nodes[-1],nodes[0]))
    result=m.analyze_projection(nodes,_wp2d_simple_edges(pairs))
    assert bool(result['cyclic_components'])==cycle
    assert result['component_count']==(1 if cycle else len(nodes))


@pytest.mark.parametrize('kind',['nodes','edges','duplicate_node','duplicate_key','bad_endpoint'])
def test_wp2d_low_level_projection_rejects_invalid_inventory(kind,monkeypatch):
    m=_wp2d_module();nodes=['a','b'];edges=_wp2d_simple_edges([('a','b')])
    if kind=='nodes':monkeypatch.setattr(m,'MAX_GRAPH_NODES',1)
    elif kind=='edges':monkeypatch.setattr(m,'MAX_GRAPH_EDGES',0)
    elif kind=='duplicate_node':nodes.append('a')
    elif kind=='duplicate_key':edges.append(deepcopy(edges[0]))
    else:edges[0]['to']='missing'
    with pytest.raises(ValueError):m.analyze_projection(nodes,edges)


def test_wp2d_empty_projection_is_observed_only_with_zero_counts():
    m=_wp2d_module();r=m.analyze_projection([],[])
    assert r=={'component_count':0,'cyclic_components':[],'result':'no_cycle_detected_in_declared_graph'}


def test_wp2d_partial_claim_set_is_not_whole_response_cycle_freedom(tmp_path):
    root=_wp2d_fixture(tmp_path);claims=load_json(root/'claims.json');claims['claim_set']['materialization_status']='partial'
    _wp2c_write(root,'claims.json',claims);report=_wp2d_run(root,_wp2d_refresh(root))
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INCOMPLETE'
    assert report['claim_materialization_status'] is None
    assert report['cycle_detection']['result'] is None;_wp2d_limits(report)


def test_wp2d_report_is_deterministic_and_leaves_input_bytes_unchanged(tmp_path):
    root=_wp2d_fixture(tmp_path);before={p.name:p.read_bytes() for p in root.iterdir()}
    a=_wp2d_run(root);b=_wp2d_run(root)
    assert a==b
    assert before=={p.name:p.read_bytes() for p in root.iterdir()}


def test_wp2d_existing_checkers_are_still_separate_and_do_not_claim_cycles():
    old=_wp2c_run(WP2D_DEMO,WP2D_PINS)
    assert old['status']=='LOCAL_RECORD_BINDINGS_CONSISTENT'
    assert old['unperformed_checks']['typed_evidence_cycle_check']['result'] is None


def _wp2d_command(root,pins=WP2D_PINS):
    return [_wp2c_sys.executable,str(WP2D_TOOL),'--bundle-root',str(root),'--input','input.json',
            '--expected-input-sha256',pins[0],'--carriers','carriers.json','--expected-carriers-sha256',pins[1],
            '--record-set','record-set.json','--expected-record-set-sha256',pins[2],
            '--binding-profile','wp2b-json-pointer-v1','--cycle-profile','typed-dependencies-v1']


@pytest.mark.parametrize('case,code',[('cyclic',0),('acyclic',0),('invalid',1),('missing',2)])
def test_wp2d_cli_codes_distinguish_measurement_from_admission(tmp_path,case,code):
    root=_wp2d_fixture(tmp_path);pins=WP2D_PINS
    if case=='acyclic':
        g=load_json(root/'graph.json');g['dependency_edges']=[];_wp2c_write(root,'graph.json',g);pins=_wp2d_refresh(root)
    elif case=='invalid':(root/'graph.json').write_bytes(b'bad')
    elif case=='missing':(root/'graph.json').unlink()
    result=_wp2c_subprocess.run(_wp2d_command(root,pins),capture_output=True,timeout=30)
    assert result.returncode==code,result.stderr
    report=json.loads(result.stdout);_wp2d_limits(report)
    if case=='cyclic':assert report['cycle_detection']['result']=='cycle_detected'


@pytest.mark.parametrize('option',['--expected-input-sha256','--expected-carriers-sha256','--expected-record-set-sha256','--binding-profile','--cycle-profile'])
def test_wp2d_cli_requires_explicit_profiles_and_expectations(option):
    command=_wp2d_command(WP2D_DEMO);index=command.index(option);del command[index:index+2]
    result=_wp2c_subprocess.run(command,capture_output=True,timeout=30)
    assert result.returncode==2 and not result.stdout


def test_wp2d_api_rejects_unrecognized_cycle_profile():
    report=_wp2d_run(profile='automatic')
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert report['cycle_detection']['result'] is None


def test_wp2d_cli_has_no_saved_approval_plugin_or_output_path():
    result=_wp2c_subprocess.run([_wp2c_sys.executable,str(WP2D_TOOL),'--help'],capture_output=True,timeout=30)
    assert result.returncode==0
    for option in [b'--saved-report',b'--plugin',b'--output',b'--trust-all']:
        assert option not in result.stdout


def test_wp2d_missing_installation_returns_no_success_json(tmp_path):
    target=tmp_path/'installation'/'tools'/WP2D_TOOL.name;target.parent.mkdir(parents=True)
    _wp2c_shutil.copyfile(WP2D_TOOL,target);command=_wp2d_command(WP2D_DEMO);command[1]=str(target)
    result=_wp2c_subprocess.run(command,capture_output=True,timeout=30)
    assert result.returncode==2 and not result.stdout
    assert b'Anchor cycle checker error:' in result.stderr


def test_wp2d_fixed_import_does_not_write_bytecode(tmp_path,monkeypatch):
    m=_wp2d_module();(tmp_path/'tools').mkdir()
    _wp2c_shutil.copyfile(WP2C_TOOL,tmp_path/'tools'/WP2C_TOOL.name)
    monkeypatch.setattr(m,'ROOT',tmp_path);previous=_wp2c_sys.dont_write_bytecode
    m.load_record_checker()
    assert _wp2c_sys.dont_write_bytecode==previous
    assert not (tmp_path/'tools/__pycache__').exists()


def test_wp2d_uses_registered_anchor_module_without_new_manifest_entries():
    for path in ['ci/tools-tests.list','ci/pytest-tests.list']:
        assert _manifest_entries(ROOT/path).count(TEST_PATH)==1
    assert WP2D_TOOL.name not in (ROOT/'ci/tools-tests.list').read_text()


@pytest.mark.parametrize('name',['anchor_integrity_dependency_graph_v0_1.schema.json','anchor_integrity_dependency_cycle_report_v0_1.schema.json'])
def test_wp2d_schemas_are_self_contained_draft_2020_12(name):
    schema=load_json(ROOT/'schemas'/name);jsonschema.Draft202012Validator.check_schema(schema)
    base=_wp2_module();base._assert_self_contained(schema)


def test_wp2d_documented_boundary_is_not_a_release_or_anchor_verdict():
    text=(ROOT/'docs/ANCHOR_INTEGRITY_v0_1_WP2D_DEPENDENCY_CYCLES.md').read_text()
    for phrase in ['declared_edges_only','Exit 0','not proof of semantic support',
                   'cycle_anchor_classification','not an atomic filesystem snapshot']:
        assert phrase in text




def test_wp2d_native_wp2a_profile_keeps_its_existing_byte_rules(tmp_path):
    root=tmp_path/'wp2a_cycles';_wp2c_shutil.copytree(WP2_DEMO,root)
    inp=load_json(root/'input.json');claims=load_json(root/'claims.json')
    graph=load_json(WP2D_DEMO/'graph.json')
    graph.update(subject=inp['subject'],claim_set_id=claims['claim_set']['claim_set_id'],dependency_edges=[])
    _wp2c_write(root,'graph.json',graph)
    inp['paradox_graph_binding']={'path':'graph.json','sha256':_wp2c_hash(root/'graph.json'),'schema_version':graph['schema_version']}
    _wp2c_write(root,'input.json',inp)
    rs=load_json(WP2C_DEMO/'record-set.json');rs.update(binding_profile='wp2a',records=[])
    _wp2c_write(root,'record-set.json',rs)
    report=_wp2d_run(root,_wp2d_refresh(root),binding='wp2a')
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_ANALYZED'
    assert report['cycle_detection']['result']=='no_cycle_detected_in_declared_graph'
    assert report['implementation']['json_pointer_module_sha256'] is None
    _wp2d_limits(report)


def test_wp2d_graph_change_during_read_is_rejected(tmp_path,monkeypatch):
    root=_wp2d_fixture(tmp_path);m=_wp2d_module();records=m.load_record_checker();base=records.load_binding_checker()
    original=base.os.fstat;inode=(root/'graph.json').stat().st_ino;calls=[]
    def changed(fd):
        stat=original(fd)
        if stat.st_ino==inode:
            calls.append(fd)
            if len(calls)==2:
                class Mutated:
                    def __getattr__(self,name):
                        return getattr(stat,name)+1 if name=='st_mtime_ns' else getattr(stat,name)
                return Mutated()
        return stat
    monkeypatch.setattr(base.os,'fstat',changed)
    monkeypatch.setattr(records,'load_binding_checker',lambda:base)
    monkeypatch.setattr(m,'load_record_checker',lambda:records)
    report=_wp2d_run(root,module=m)
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert any('carrier_changed_during_read' in i['code'] for i in report['issues'])
    assert report['cycle_detection']['result'] is None


def test_wp2d_bundle_cannot_supply_a_verifier_or_cycle_implementation(tmp_path):
    root=_wp2d_fixture(tmp_path);graph=load_json(root/'graph.json')
    graph['algorithm_path']='evil.py';_wp2c_write(root,'graph.json',graph)
    (root/'evil.py').write_text("raise AssertionError('artifact code executed')")
    report=_wp2d_run(root,_wp2d_refresh(root))
    assert report['status']=='LOCAL_DEPENDENCY_GRAPH_INVALID'
    assert report['cycle_detection']['result'] is None


def test_wp2d_installation_schemas_cannot_resolve_external_refs(tmp_path,monkeypatch):
    m=_wp2d_module();base=m.load_record_checker().load_binding_checker()
    (tmp_path/'schemas').mkdir()
    for name in m.SCHEMAS.values():
        _wp2c_shutil.copyfile(ROOT/'schemas'/name,tmp_path/'schemas'/name)
    path=tmp_path/'schemas'/m.SCHEMAS['graph'];value=load_json(path);value['$ref']='https://invalid.example/not_allowed'
    path.write_text(json.dumps(value));monkeypatch.setattr(m,'ROOT',tmp_path)
    with pytest.raises(base.BindingError):m.CycleSchemas(base)


def test_wp2d_cli_reads_only_and_creates_no_bundle_files(tmp_path):
    root=_wp2d_fixture(tmp_path);before={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
    command=_wp2d_command(root)
    result=_wp2c_subprocess.run(command,capture_output=True,timeout=30)
    assert result.returncode==0
    assert before=={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_wp2d_reordered_graph_declarations_keep_the_same_projection(tmp_path):
    root=_wp2d_fixture(tmp_path);graph=load_json(root/'graph.json')
    graph['dependency_edges'].append(_wp2d_edge(source='claim-2',target='claim-2'))
    _wp2c_write(root,'graph.json',graph);a=_wp2d_run(root,_wp2d_refresh(root))
    graph['dependency_edges'].reverse();_wp2c_write(root,'graph.json',graph)
    b=_wp2d_run(root,_wp2d_refresh(root))
    for key in ['nodes','edges','cyclic_components','cycle_detection','counts']:
        assert a[key]==b[key]
    assert a['graph_binding']['observed_sha256']!=b['graph_binding']['observed_sha256']


# WP2E: exact record signatures under a caller-pinned, separate policy.
# The following private seed is PUBLIC RFC 8032 test material, never a credential.
import tempfile as _wp2e_tempfile

WP2E_TOOL = ROOT / 'tools/check_anchor_integrity_record_signatures_v0_1.py'
WP2E_DEMO = ROOT / 'examples/anchor_integrity_v0_1/wp2e_record_signatures'
WP2E_EPOCH = 1793836800
WP2E_SEED = bytes.fromhex('4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb')
WP2E_PINS = (
    'd7d16dfccf2dce237060e6b77fbb7da907227b1bd56f1275cfb623ce81cd59a8',
    '70a4d15ee35db21a605ef283c531724d921658fa8bc46ca68f6867925b2c91c4',
    'a70299602a9aae82adcd4ff17278eef5a802ad72e05dbdae6fec64a9f98f188e',
    '6dd6feb77a3c4cc4520e2f4950906a96a8e533d9d23455f8d0da77f47ff1ae8a',
    '833e2a5c9cdbb021d4c59f0c5269e04cebe9b6c6c719ccc872a52d679950bb32',
)


def _wp2e_module():
    spec = _wp2c_importlib.spec_from_file_location('wp2e_test_checker', WP2E_TOOL)
    module = _wp2c_importlib.module_from_spec(spec)
    old = _wp2c_sys.dont_write_bytecode
    _wp2c_sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        _wp2c_sys.dont_write_bytecode = old
    return module


def _wp2e_fixture(tmp_path):
    root = tmp_path / 'signed-example'
    _wp2c_shutil.copytree(WP2E_DEMO, root)
    return root / 'bundle', root / 'trust'


def _wp2e_pins(pair):
    bundle, trust = pair
    return (*(_wp2c_hash(bundle / n) for n in ('input.json', 'carriers.json', 'record-set.json', 'signatures.json')),
            _wp2c_hash(trust / 'policy.json'))


def _wp2e_run(pair=None, pins=None, module=None, **options):
    bundle, trust = pair or (WP2E_DEMO / 'bundle', WP2E_DEMO / 'trust')
    pins = pins or WP2E_PINS
    m = module or _wp2e_module()
    kwargs = dict(trust_root=trust, trust_policy_path='policy.json', expected_trust_policy_sha256=pins[4],
                  binding_profile='wp2b-json-pointer-v1', signature_profile=m.PROFILE,
                  trust_domain='TEST', verification_time_epoch=WP2E_EPOCH)
    kwargs.update(options)
    return m.verify_signatures(bundle, 'input.json', pins[0], 'carriers.json', pins[1],
                               'record-set.json', pins[2], 'signatures.json', pins[3], **kwargs)


def _wp2e_limits(report):
    assert report['candidate_status'] == 'diagnostic_only'
    assert report['authority_effect'] == 'none'
    for name in ('release_authority_activation', 'requested_checks_complete',
                 'accepted_as_semantic_support', 'accepted_as_independent_anchor'):
        assert report[name] is False
    assert report['time_source'] == 'caller_supplied_not_authenticated'
    for check in report['unperformed_checks'].values():
        assert check['status'] == 'not_run' and check['result'] is None and check['reason']
    for row in report['records']:
        assert row['accepted_as_semantic_support'] is False
        assert row['accepted_as_independent_anchor'] is False


def _wp2e_has(report, code):
    return any(i['code'] == code for i in report['issues'])


def _wp2e_sign(message, seed=WP2E_SEED):
    # Real OpenSSL signing in tests only. The production tool has no signing API.
    with _wp2e_tempfile.TemporaryDirectory(prefix='anchor-test-sign-', dir='/tmp') as tmp:
        d = Path(tmp)
        (d / 'key.der').write_bytes(bytes.fromhex('302e020100300506032b657004220420') + seed)
        (d / 'message').write_bytes(message)
        p = _wp2c_subprocess.run(['/usr/bin/openssl', 'pkeyutl', '-sign', '-keyform', 'DER',
                                  '-inkey', 'key.der', '-rawin', '-in', 'message', '-provider', 'default'],
                                 cwd=d, env={'PATH':'/usr/bin:/bin','LC_ALL':'C','OPENSSL_CONF':'/dev/null'},
                                 capture_output=True, timeout=10)
        assert p.returncode == 0, p.stderr
        assert len(p.stdout) == 64
        return p.stdout


def _wp2e_resign(pair, sync_record_roots=False):
    b, t = pair
    if sync_record_roots:
        _wp2c_repin(b, True)
    m = _wp2e_module()
    policy = load_json(t / 'policy.json')
    policy_hash = _wp2c_hash(t / 'policy.json')
    record_set = load_json(b / 'record-set.json')
    manifest = load_json(b / 'signatures.json')
    manifest['record_set_binding'] = {'path':'record-set.json','sha256':_wp2c_hash(b / 'record-set.json')}
    manifest['trust_policy_sha256'] = policy_hash
    manifest['signatures'] = []
    for n, entry in enumerate(record_set['records'], 1):
        raw = (b / entry['path']).read_bytes()
        sig = {'schema_version':'anchor_integrity_record_signature_v0_1', 'candidate_status':'diagnostic_only',
               'authority_effect':'none','release_authority_activation':False,'signature_suite':'ed25519',
               'signature_domain':m.DOMAIN,'record_id':entry['record_id'],'record_sha256':m.digest(raw),
               'trust_policy_sha256':policy_hash,'key_id':policy['keys'][0]['key_id']}
        sig['signature_hex'] = _wp2e_sign(m.signing_bytes(policy_hash, sig['key_id'], raw)).hex()
        name = 'signature-' + str(n) + '.json'
        _wp2c_write(b, name, sig)
        manifest['signatures'].append({'record_id':entry['record_id'],'path':name,'sha256':_wp2c_hash(b / name)})
    _wp2c_write(b, 'signatures.json', manifest)
    return _wp2e_pins(pair)


def _wp2e_refresh_envelope_manifest(pair):
    b, _ = pair
    manifest = load_json(b / 'signatures.json')
    for entry in manifest['signatures']:
        if (b / entry['path']).is_file():
            entry['sha256'] = _wp2c_hash(b / entry['path'])
    _wp2c_write(b, 'signatures.json', manifest)
    return _wp2e_pins(pair)


def test_wp2e_real_signature_demo_and_policy_boundary():
    assert _wp2e_pins((WP2E_DEMO/'bundle', WP2E_DEMO/'trust')) == WP2E_PINS
    r = _wp2e_run()
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_VERIFIED'
    assert r['counts'] == {'required_records':1,'listed_signatures':1,'admitted_records':1}
    assert r['signer_authentication']['result'] == 'test_key_signatures_verified'
    assert r['records'][0]['signature_check']['result'] == 'valid'
    assert r['records'][0]['policy_check']['result'] == 'authorized'
    _wp2e_limits(r)


@pytest.mark.parametrize('which', range(5))
@pytest.mark.parametrize('bad', ['0'*64, 'ABC', None])
def test_wp2e_every_expected_root_is_required_and_checked(which, bad):
    pins = list(WP2E_PINS); pins[which] = bad
    r = _wp2e_run(pins=pins)
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_INVALID'
    assert r['signer_authentication']['result'] is None
    _wp2e_limits(r)


@pytest.mark.parametrize('name', ['input.json','carriers.json','record-set.json','source.json','record-1.json',
                                  'signature-1.json','signatures.json','policy.json'])
def test_wp2e_missing_material_never_authenticates(tmp_path, name):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    (t / name if name == 'policy.json' else b / name).unlink()
    r = _wp2e_run(pair)
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_INCOMPLETE'
    assert r['signer_authentication']['status'] == 'not_run'


@pytest.mark.parametrize('field,value,code', [
    ('state','revoked','signer_key_revoked'),
    ('not_before_epoch',WP2E_EPOCH+1,'signer_key_outside_validity'),
    ('not_after_epoch',WP2E_EPOCH,'signer_key_outside_validity'),
    ('relation_types',['supports'],'signer_relation_scope_mismatch'),
    ('results',['supported'],'signer_result_scope_mismatch'),
])
def test_wp2e_authorization_constraints_are_enforced_after_real_resigning(tmp_path, field, value, code):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    policy = load_json(t / 'policy.json'); policy['keys'][0][field] = value
    _wp2c_write(t, 'policy.json', policy)
    r = _wp2e_run(pair, _wp2e_resign(pair))
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_INVALID'
    assert _wp2e_has(r, code)
    assert r['records'][0]['policy_check']['result'] == 'denied'


@pytest.mark.parametrize('field', ['verifier_id','method_id','method_version','implementation_sha256'])
def test_wp2e_signature_key_cannot_impersonate_another_verifier_tuple(tmp_path, field):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    p = load_json(t / 'policy.json'); p['keys'][0]['verifier'][field] = '0'*64 if field == 'implementation_sha256' else 'other'
    _wp2c_write(t, 'policy.json', p)
    r = _wp2e_run(pair, _wp2e_resign(pair))
    assert _wp2e_has(r, 'signer_verifier_scope_mismatch')


@pytest.mark.parametrize('field', ['subject_id','run_id'])
def test_wp2e_policy_subject_and_run_are_not_wildcards(tmp_path, field):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    p = load_json(t / 'policy.json'); p['subject'][field] = 'different'
    _wp2c_write(t, 'policy.json', p)
    r = _wp2e_run(pair, _wp2e_resign(pair))
    assert _wp2e_has(r, 'policy_subject_mismatch')
    assert r['records'] == []


@pytest.mark.parametrize('epoch,ok', [(1793750399,False),(1793750400,True),(1793923199,True),(1793923200,False)])
def test_wp2e_validity_interval_is_half_open_at_caller_supplied_time(epoch, ok):
    r = _wp2e_run(verification_time_epoch=epoch)
    assert (r['status'] == 'LOCAL_RECORD_SIGNATURES_VERIFIED') is ok
    assert r['unperformed_checks']['trusted_clock_verification']['result'] is None


@pytest.mark.parametrize('bad', [-1, True, 1.5, '1793836800', None, 253402300800])
def test_wp2e_invalid_caller_time_is_not_coerced(bad):
    with pytest.raises(ValueError):
        _wp2e_run(verification_time_epoch=bad)


def test_wp2e_test_policy_cannot_be_used_as_operator_policy():
    r = _wp2e_run(trust_domain='OPERATOR')
    assert _wp2e_has(r, 'trust_domain_mismatch')
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_INVALID'


def test_wp2e_operator_policy_is_an_explicit_caller_trust_assumption(tmp_path):
    # Synthetic test of the OPERATOR branch, not a real operational credential.
    pair = _wp2e_fixture(tmp_path); b, t = pair
    p = load_json(t / 'policy.json'); p['trust_domain'] = 'OPERATOR'
    _wp2c_write(t, 'policy.json', p)
    r = _wp2e_run(pair, _wp2e_resign(pair), trust_domain='OPERATOR')
    assert r['signer_authentication']['result'] == 'authorized_key_signatures_verified'
    assert r['unperformed_checks']['trust_policy_authorization_verification']['result'] is None
    _wp2e_limits(r)


@pytest.mark.parametrize('kind', ['same','inside','parent'])
def test_wp2e_policy_root_must_be_disjoint_from_evidence_root(tmp_path, kind):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    root = b if kind == 'same' else b/'trust' if kind == 'inside' else b.parent
    if kind == 'inside': root.mkdir()
    r = _wp2e_run(pair, trust_root=root)
    assert _wp2e_has(r, 'trust_root_not_separate_from_bundle')


@pytest.mark.parametrize('field,value', [('record_id','other-record'),('record_sha256','0'*64),
                                        ('trust_policy_sha256','0'*64)])
def test_wp2e_envelope_subject_substitution_rejected_even_when_rehashed(tmp_path, field, value):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    s = load_json(b / 'signature-1.json'); s[field] = value
    _wp2c_write(b, 'signature-1.json', s)
    r = _wp2e_run(pair, _wp2e_refresh_envelope_manifest(pair))
    assert _wp2e_has(r, 'signature_subject_mismatch')


@pytest.mark.parametrize('field,value', [('signature_suite','none'),('signature_domain','wrong'),
 ('public_key_hex','0'*64),('signed_message','invented'),('release_authority_activation',True),
 ('authority_effect','release'),('candidate_status','active')])
def test_wp2e_envelope_cannot_select_algorithm_key_or_authority(tmp_path, field, value):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    s = load_json(b / 'signature-1.json'); s[field] = value
    _wp2c_write(b, 'signature-1.json', s)
    r = _wp2e_run(pair, _wp2e_refresh_envelope_manifest(pair))
    assert _wp2e_has(r, 'schema_invalid_signature_signature')


@pytest.mark.parametrize('bad', ['0'*128,'ff'*64,'ab', 'g'*128, '', 'AB'*64])
def test_wp2e_invalid_or_noncanonical_signature_bytes_rejected(tmp_path, bad):
    pair = _wp2e_fixture(tmp_path); b, _ = pair
    s = load_json(b / 'signature-1.json'); s['signature_hex'] = bad
    _wp2c_write(b, 'signature-1.json', s)
    r = _wp2e_run(pair, _wp2e_refresh_envelope_manifest(pair))
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_INVALID'


def test_wp2e_envelope_cannot_nominate_an_unlisted_key(tmp_path):
    pair = _wp2e_fixture(tmp_path); b, _ = pair
    s = load_json(b / 'signature-1.json'); s['key_id'] = 'unknown'
    _wp2c_write(b, 'signature-1.json', s)
    r = _wp2e_run(pair, _wp2e_refresh_envelope_manifest(pair))
    assert _wp2e_has(r, 'signer_key_not_authorized')


def test_wp2e_signature_is_bound_to_policy_bytes_not_just_key(tmp_path):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    p = load_json(t / 'policy.json'); p['policy_id'] = 'another-policy'
    _wp2c_write(t, 'policy.json', p); ph = _wp2c_hash(t / 'policy.json')
    s = load_json(b / 'signature-1.json'); s['trust_policy_sha256'] = ph
    _wp2c_write(b, 'signature-1.json', s)
    a = load_json(b / 'signatures.json'); a['trust_policy_sha256'] = ph
    _wp2c_write(b, 'signatures.json', a)
    r = _wp2e_run(pair, _wp2e_refresh_envelope_manifest(pair))
    assert _wp2e_has(r, 'record_signature_invalid')


def test_wp2e_signature_is_bound_to_key_id_even_if_public_key_is_unchanged(tmp_path):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    p = load_json(t / 'policy.json'); p['keys'][0]['key_id'] = 'renamed-key'
    _wp2c_write(t, 'policy.json', p); ph = _wp2c_hash(t / 'policy.json')
    s = load_json(b / 'signature-1.json'); s.update(key_id='renamed-key',trust_policy_sha256=ph)
    _wp2c_write(b, 'signature-1.json', s)
    a = load_json(b / 'signatures.json'); a['trust_policy_sha256'] = ph
    _wp2c_write(b, 'signatures.json', a)
    r = _wp2e_run(pair, _wp2e_refresh_envelope_manifest(pair))
    assert _wp2e_has(r, 'record_signature_invalid')


def test_wp2e_reformatted_record_with_refreshed_hashes_requires_new_signature(tmp_path):
    pair = _wp2e_fixture(tmp_path); b, _ = pair
    (b / 'record-1.json').write_text(json.dumps(load_json(b/'record-1.json'),separators=(',',':')))
    rs = load_json(b/'record-set.json'); rs['records'][0]['sha256'] = _wp2c_hash(b/'record-1.json')
    _wp2c_write(b,'record-set.json',rs)
    s = load_json(b/'signature-1.json'); s['record_sha256'] = rs['records'][0]['sha256']
    _wp2c_write(b,'signature-1.json',s)
    a = load_json(b/'signatures.json'); a['record_set_binding']['sha256'] = _wp2c_hash(b/'record-set.json')
    _wp2c_write(b,'signatures.json',a)
    r = _wp2e_run(pair,_wp2e_refresh_envelope_manifest(pair))
    assert r['record_check']['status'] == 'LOCAL_RECORD_BINDINGS_CONSISTENT'
    assert _wp2e_has(r,'record_signature_invalid')


@pytest.mark.parametrize('kind', ['empty','duplicate-id','duplicate-path','orphan','wrong-set','wrong-policy'])
def test_wp2e_manifest_coverage_and_exact_roots(tmp_path, kind):
    pair = _wp2e_fixture(tmp_path); b, _ = pair
    a = load_json(b/'signatures.json')
    if kind == 'empty': a['signatures'] = []
    elif kind == 'duplicate-id': a['signatures'].append(deepcopy(a['signatures'][0]))
    elif kind in ('duplicate-path','orphan'):
        e = deepcopy(a['signatures'][0]); e['record_id'] = 'unlisted-record'
        if kind == 'orphan': e['path'] = 'orphan.json'
        a['signatures'].append(e)
    elif kind == 'wrong-set': a['record_set_binding']['sha256'] = '0'*64
    else: a['trust_policy_sha256'] = '0'*64
    _wp2c_write(b,'signatures.json',a)
    r = _wp2e_run(pair,_wp2e_pins(pair))
    expected = 'LOCAL_RECORD_SIGNATURES_INCOMPLETE' if kind == 'empty' else 'LOCAL_RECORD_SIGNATURES_INVALID'
    assert r['status'] == expected
    assert r['signer_authentication']['result'] is None


def test_wp2e_invalid_orphan_takes_precedence_over_missing_signature(tmp_path):
    pair = _wp2e_fixture(tmp_path); b, _ = pair
    a = load_json(b/'signatures.json'); a['signatures'][0]['record_id'] = 'orphan'
    _wp2c_write(b,'signatures.json',a)
    r = _wp2e_run(pair,_wp2e_pins(pair))
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_INVALID'
    assert {x['severity'] for x in r['issues']} == {'invalid','incomplete'}


def test_wp2e_zero_records_never_yield_positive_authentication(tmp_path):
    pair = _wp2e_fixture(tmp_path); b, _ = pair
    rp = load_json(b/'relations.json'); rp['relations'] = []
    rs = load_json(b/'record-set.json'); rs['records'] = []
    _wp2c_write(b,'relations.json',rp); _wp2c_write(b,'record-set.json',rs)
    pins = _wp2e_resign(pair,True)
    r = _wp2e_run(pair,pins)
    assert r['record_check']['status'] == 'LOCAL_RECORD_BINDINGS_CONSISTENT'
    assert _wp2e_has(r,'no_records_to_authenticate')
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_INCOMPLETE'


def test_wp2e_two_records_are_authenticated_separately(tmp_path):
    pair = _wp2e_fixture(tmp_path); b, _ = pair
    rp = load_json(b/'relations.json'); second = deepcopy(rp['relations'][0])
    second.update(binding_id='binding-2',verifier_record_id='synthetic-record-2')
    rp['relations'].append(second); _wp2c_write(b,'relations.json',rp)
    rec = load_json(b/'record-1.json'); rec['record_id'] = 'synthetic-record-2'; rec['binding']['binding_id'] = 'binding-2'
    _wp2c_write(b,'record-2.json',rec)
    rs = load_json(b/'record-set.json'); e = deepcopy(rs['records'][0])
    e.update(record_id='synthetic-record-2',binding_id='binding-2',path='record-2.json')
    rs['records'].append(e); _wp2c_write(b,'record-set.json',rs)
    r = _wp2e_run(pair,_wp2e_resign(pair,True))
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_VERIFIED'
    assert r['counts'] == {'required_records':2,'listed_signatures':2,'admitted_records':2}
    (b/'signature-2.json').unlink()
    r = _wp2e_run(pair,_wp2e_pins(pair))
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_INCOMPLETE'
    assert r['counts']['admitted_records'] == 1


@pytest.mark.parametrize('filename', ['policy.json','signatures.json','signature-1.json'])
@pytest.mark.parametrize('kind', ['symlink','hardlink','directory','fifo'])
def test_wp2e_new_files_preserve_safe_file_boundary(tmp_path, filename, kind):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    p = (t if filename == 'policy.json' else b)/filename
    raw = p.read_bytes(); p.unlink()
    if kind == 'directory': p.mkdir()
    elif kind == 'fifo': _wp2c_os.mkfifo(p)
    else:
        target = tmp_path/'target'; target.write_bytes(raw)
        if kind == 'symlink': p.symlink_to(target)
        else: _wp2c_os.link(target,p)
    assert _wp2e_run(pair)['status'] == 'LOCAL_RECORD_SIGNATURES_INVALID'


@pytest.mark.parametrize('path', ['../escape','/tmp/key','x\\y','./policy.json','a//b','policy.json.'])
def test_wp2e_unsafe_policy_paths_rejected(path):
    r = _wp2e_run(trust_policy_path=path)
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_INVALID'


@pytest.mark.parametrize('alias', ['input.json','carriers.json','record-set.json','record-1.json','source.json','signatures.json'])
def test_wp2e_signatures_cannot_alias_existing_carrier_roles(tmp_path, alias):
    pair = _wp2e_fixture(tmp_path); b, _ = pair
    a = load_json(b/'signatures.json'); a['signatures'][0]['path'] = alias
    _wp2c_write(b,'signatures.json',a)
    assert _wp2e_run(pair,_wp2e_pins(pair))['status'] == 'LOCAL_RECORD_SIGNATURES_INVALID'


@pytest.mark.parametrize('name', ['policy.json','signatures.json','signature-1.json'])
@pytest.mark.parametrize('bad', [b'{"x":1,"x":2}', b'{"x":NaN}', b'[]', b'\xff', b'{}\n{}'])
def test_wp2e_strict_json_and_closed_shapes_are_required(tmp_path, name, bad):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    p = (t if name == 'policy.json' else b)/name; p.write_bytes(bad)
    pins = _wp2e_refresh_envelope_manifest(pair) if name == 'signature-1.json' else _wp2e_pins(pair)
    assert _wp2e_run(pair,pins)['status'] == 'LOCAL_RECORD_SIGNATURES_INVALID'


@pytest.mark.parametrize('change', ['duplicate-id','duplicate-key','wrong-key-digest','empty-interval'])
def test_wp2e_policy_identity_and_key_integrity(tmp_path, change):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    p = load_json(t/'policy.json')
    if change.startswith('duplicate'):
        k = deepcopy(p['keys'][0])
        if change == 'duplicate-key': k['key_id'] = 'alias'
        p['keys'].append(k)
    elif change == 'wrong-key-digest': p['keys'][0]['public_key_sha256'] = '0'*64
    else: p['keys'][0]['not_after_epoch'] = p['keys'][0]['not_before_epoch']
    _wp2c_write(t,'policy.json',p)
    r = _wp2e_run(pair,_wp2e_pins(pair))
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_INVALID' and r['records'] == []


@pytest.mark.parametrize('y', [0,1,2**255-20,
 2707385501144840649318225287225658788936804267575313519463743609750303402022,
 55188659117513257062467267217118295137698188065244968500265048394206261417927,
 2**255-19,2**255-18,2**255-1])
@pytest.mark.parametrize('sign', [0,1])
def test_wp2e_torsion_and_noncanonical_keys_rejected_before_backend(tmp_path, y, sign):
    pair = _wp2e_fixture(tmp_path); b, t = pair; m = _wp2e_module()
    raw = (y | (sign<<255)).to_bytes(32,'little')
    assert not m.point_encoding_allowed(raw)
    p = load_json(t/'policy.json'); p['keys'][0].update(public_key_hex=raw.hex(),public_key_sha256=m.digest(raw))
    _wp2c_write(t,'policy.json',p)
    r = _wp2e_run(pair,_wp2e_pins(pair),module=m)
    assert _wp2e_has(r,'policy_weak_or_noncanonical_key')
    assert r['implementation']['crypto_backend'] is None


def test_wp2e_backend_known_answer_and_weak_key_forgery_controls():
    m = _wp2e_module(); v = m.OpenSSLVerifier()
    assert v.verify(m.KAT_PUBLIC,m.KAT_SIGNATURE,m.KAT_MESSAGE)
    assert not v.verify(m.KAT_PUBLIC,m.KAT_SIGNATURE,b'changed')
    for key, sig in [(bytes(32),bytes(64)),(b'\1'+bytes(31),b'\1'+bytes(63))]:
        assert not v.verify(key,sig,b'arbitrary message')
    assert not v.verify(m.KAT_PUBLIC,m.KAT_SIGNATURE[:32]+m.SCALAR_ORDER.to_bytes(32,'little'),m.KAT_MESSAGE)


def test_wp2e_no_fallback_when_backend_unavailable(tmp_path, monkeypatch, capsys):
    m = _wp2e_module()
    def fail(): raise RuntimeError('backend_missing')
    monkeypatch.setattr(m,'OpenSSLVerifier',fail)
    rc = m.main(_wp2e_command()[2:])
    captured = capsys.readouterr()
    assert rc == 2 and captured.out == '' and 'RuntimeError' in captured.err


@pytest.mark.parametrize('kind', ['positive','negative'])
def test_wp2e_selftest_rejects_broken_backend(monkeypatch, kind):
    m = _wp2e_module()
    monkeypatch.setattr(m.OpenSSLVerifier,'verify',lambda *args: kind == 'negative')
    with pytest.raises(RuntimeError,match='self_test_failed'):
        m.OpenSSLVerifier()


def test_wp2e_subprocess_uses_fixed_executable_and_clean_environment(monkeypatch):
    m = _wp2e_module(); real = m.subprocess.run; seen = []
    monkeypatch.setenv('OPENSSL_CONF','/untrusted/config')
    monkeypatch.setenv('LD_PRELOAD','/untrusted/library')
    def checked(command,**kw):
        seen.append(command)
        assert command[0] == '/usr/bin/openssl'
        assert kw['shell'] is False and kw['close_fds'] is True
        assert kw['env']['OPENSSL_CONF'] == '/dev/null'
        assert 'LD_PRELOAD' not in kw['env'] and 'OPENSSL_MODULES' not in kw['env']
        assert 0 < kw['timeout'] <= 5
        return real(command,**kw)
    monkeypatch.setattr(m.subprocess,'run',checked)
    r = _wp2e_run(module=m)
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_VERIFIED' and len(seen) == 4


def test_wp2e_crypto_deadline_is_fail_closed(monkeypatch):
    m = _wp2e_module(); v = m.OpenSSLVerifier(); v.deadline = -1
    with pytest.raises(RuntimeError,match='time_budget'):
        v.verify(m.KAT_PUBLIC,m.KAT_SIGNATURE,m.KAT_MESSAGE)


@pytest.mark.parametrize('name', ['MAX_POLICY_BYTES','MAX_SIGNATURE_BYTES'])
def test_wp2e_metadata_size_limits(tmp_path, monkeypatch, name):
    pair = _wp2e_fixture(tmp_path); m = _wp2e_module(); monkeypatch.setattr(m,name,1)
    r = _wp2e_run(pair,module=m)
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_INVALID'


def test_wp2e_per_invocation_record_limit(tmp_path, monkeypatch):
    pair = _wp2e_fixture(tmp_path); m = _wp2e_module(); monkeypatch.setattr(m,'MAX_SIGNATURES',0)
    r = _wp2e_run(pair,module=m)
    assert _wp2e_has(r,'base.signature_record_limit')


def test_wp2e_record_bytes_retained_by_fresh_base_not_reopened(tmp_path, monkeypatch):
    pair = _wp2e_fixture(tmp_path); b, _ = pair; m = _wp2e_module()
    previous = m.SignatureReview.capture_previous
    def change_after(self,*args):
        result = previous(self,*args)
        (b/'record-1.json').write_text('changed after read')
        return result
    monkeypatch.setattr(m.SignatureReview,'capture_previous',change_after)
    r = _wp2e_run(pair,module=m)
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_VERIFIED'
    assert r['records'][0]['record_sha256'] != _wp2c_hash(b/'record-1.json')


def test_wp2e_saved_success_report_cannot_replace_fresh_binding(tmp_path):
    pair = _wp2e_fixture(tmp_path); b, _ = pair
    (b/'success.json').write_bytes(_wp2e_module().report_bytes(_wp2e_run()))
    (b/'source.json').write_text('tampered')
    r = _wp2e_run(pair)
    assert r['record_check']['status'] == 'LOCAL_RECORD_BINDINGS_INVALID'
    assert r['records'] == [] and r['signer_authentication']['result'] is None


def test_wp2e_signed_supported_declaration_is_not_semantic_support(tmp_path):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    rp = load_json(b/'relations.json'); rp['relations'][0]['relation_verification']['result'] = 'supported'
    rec = load_json(b/'record-1.json'); rec['verification']['result'] = 'supported'
    p = load_json(t/'policy.json'); p['keys'][0]['results'] = ['supported']
    _wp2c_write(b,'relations.json',rp); _wp2c_write(b,'record-1.json',rec); _wp2c_write(t,'policy.json',p)
    r = _wp2e_run(pair,_wp2e_resign(pair,True))
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_VERIFIED'
    _wp2e_limits(r)


def test_wp2e_signing_cyclic_fixture_does_not_anchor_cycle(tmp_path):
    pair = _wp2e_fixture(tmp_path); b, t = pair
    for p in WP2D_DEMO.iterdir():
        if p.is_file(): (b/p.name).write_bytes(p.read_bytes())
    p = load_json(t/'policy.json'); p['keys'][0]['relation_types'] = ['supports']
    _wp2c_write(t,'policy.json',p)
    r = _wp2e_run(pair,_wp2e_resign(pair))
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_VERIFIED'
    cycle = _wp2d_run(b,_wp2c_pins(b))
    assert cycle['cycle_detection']['result'] == 'cycle_detected'
    assert cycle['cycle_anchor_classification']['result'] is None
    assert r['unperformed_checks']['independent_anchor_admission']['result'] is None


@pytest.fixture(scope='module')
def wp2e_valid_report():
    return _wp2e_run()


@pytest.mark.parametrize('field', ['release_authority_activation','requested_checks_complete',
 'accepted_as_semantic_support','accepted_as_independent_anchor'])
def test_wp2e_report_cannot_promote_authority(wp2e_valid_report,field):
    r = deepcopy(wp2e_valid_report); r[field] = True
    assert_invalid('anchor_integrity_record_signature_report_v0_1.schema.json',r)


@pytest.mark.parametrize('part', _wp2e_module().UNPERFORMED)
def test_wp2e_report_cannot_complete_unperformed_stages(wp2e_valid_report,part):
    r = deepcopy(wp2e_valid_report); r['unperformed_checks'][part] = {'status':'completed','result':'verified','reason':None}
    assert_invalid('anchor_integrity_record_signature_report_v0_1.schema.json',r)


@pytest.mark.parametrize('part', ['signature_check','policy_check'])
def test_wp2e_admitted_record_requires_actual_completed_checks(wp2e_valid_report,part):
    r = deepcopy(wp2e_valid_report); r['records'][0][part] = {'status':'not_run','result':None,'reason':'not_done'}
    assert_invalid('anchor_integrity_record_signature_report_v0_1.schema.json',r)


def test_wp2e_test_result_cannot_be_relabelled_as_operator_result(wp2e_valid_report):
    r = deepcopy(wp2e_valid_report); r['signer_authentication']['result'] = 'authorized_key_signatures_verified'
    assert_invalid('anchor_integrity_record_signature_report_v0_1.schema.json',r)


@pytest.mark.parametrize('schema', list(_wp2e_module().SCHEMAS.values()))
def test_wp2e_new_schemas_are_closed_self_contained_draft202012(schema):
    value = load_json(SCHEMA_DIR/schema)
    jsonschema.Draft202012Validator.check_schema(value)
    _wp2_module()._assert_self_contained(value)
    assert value['additionalProperties'] is False


def _wp2e_command():
    b, t = WP2E_DEMO/'bundle', WP2E_DEMO/'trust'
    cmd = [_wp2c_sys.executable,str(WP2E_TOOL),'--bundle-root',str(b)]
    for n,pin in zip(('input','carriers','record-set','signatures'),WP2E_PINS[:4]):
        cmd += ['--'+n,n+'.json','--expected-'+n+'-sha256',pin]
    return cmd+['--trust-root',str(t),'--trust-policy','policy.json','--expected-trust-policy-sha256',WP2E_PINS[4],
                '--binding-profile','wp2b-json-pointer-v1','--signature-profile','pinned-ed25519-record-signers-v1',
                '--trust-domain','TEST','--verification-time-epoch',str(WP2E_EPOCH)]


def test_wp2e_cli_really_verifies_and_stdout_is_only_report():
    result = _wp2c_subprocess.run(_wp2e_command(),capture_output=True,timeout=30)
    assert result.returncode == 0 and result.stderr == b''
    r = json.loads(result.stdout)
    assert r['status'] == 'LOCAL_RECORD_SIGNATURES_VERIFIED'
    _wp2e_limits(r)


@pytest.mark.parametrize('option', ['--expected-input-sha256','--expected-carriers-sha256','--expected-record-set-sha256',
 '--expected-signatures-sha256','--trust-root','--trust-policy','--expected-trust-policy-sha256',
 '--binding-profile','--signature-profile','--trust-domain','--verification-time-epoch'])
def test_wp2e_cli_has_no_implicit_trust_defaults(option):
    cmd = _wp2e_command(); i = cmd.index(option); del cmd[i:i+2]
    result = _wp2c_subprocess.run(cmd,capture_output=True,timeout=30)
    assert result.returncode == 2 and result.stdout == b''


def test_wp2e_no_saved_report_or_output_overwrite_cli(tmp_path):
    target = tmp_path/'status.json'; target.write_bytes(b'unchanged')
    result = _wp2c_subprocess.run(_wp2e_command()+['--output',str(target),'--saved-report','success.json'],capture_output=True,timeout=30)
    assert result.returncode == 2 and not result.stdout
    assert target.read_bytes() == b'unchanged'


def test_wp2e_deterministic_report_and_no_input_changes(tmp_path):
    pair = _wp2e_fixture(tmp_path); root = pair[0].parent
    before = {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    a, b = _wp2e_run(pair), _wp2e_run(pair)
    assert a == b
    after = {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert before == after


def test_wp2e_existing_manifest_registration_is_reused():
    for name in ('ci/tools-tests.list','ci/pytest-tests.list'):
        assert _manifest_entries(ROOT/name).count(TEST_PATH) == 1


@pytest.mark.parametrize('part', ['public','nonce','scalar'])
def test_wp2e_invalid_group_encodings_do_not_reach_openssl(monkeypatch, part):
    m = _wp2e_module(); v = m.OpenSSLVerifier()
    def forbidden(*args, **kwargs):
        raise AssertionError('invalid encoding reached external verifier')
    monkeypatch.setattr(v, '_run', forbidden)
    key = m.KAT_PUBLIC
    sig = m.KAT_SIGNATURE
    if part == 'public': key = b'\1' + bytes(31)
    elif part == 'nonce': sig = b'\1' + bytes(31) + sig[32:]
    else: sig = sig[:32] + bytes(32)
    assert not v.verify(key, sig, m.KAT_MESSAGE)


def test_wp2e_message_domain_and_field_delimiters_are_exact():
    m = _wp2e_module()
    raw = b'{"record": "\\u00e9"}\r\n'
    expected = b'PULSEMECH-ANCHOR-RECORD-SIGNATURE-V1\0' + b'0'*64 + b'\0key-1\0' + raw
    assert m.signing_bytes('0'*64, 'key-1', raw) == expected
    with pytest.raises(ValueError):
        m.signing_bytes('0'*64, 'key\0other', raw)


def test_wp2e_signature_byte_mutation_fails_even_when_all_outer_hashes_match(tmp_path):
    pair = _wp2e_fixture(tmp_path); b, _ = pair
    sig = load_json(b/'signature-1.json'); raw = bytearray.fromhex(sig['signature_hex'])
    raw[40] ^= 1; sig['signature_hex'] = raw.hex()
    _wp2c_write(b,'signature-1.json',sig)
    r = _wp2e_run(pair,_wp2e_refresh_envelope_manifest(pair))
    assert _wp2e_has(r,'record_signature_invalid')
    assert r['records'][0]['signature_check']['result'] == 'invalid'


def test_wp2e_no_signing_or_trusted_key_default_in_production_cli():
    source = WP2E_TOOL.read_text()
    assert "'-sign'" not in source and 'Ed25519PrivateKey' not in source
    assert 'WP2E_SEED' not in source
    assert "parser.add_argument('--trust-policy', required=True)" in source



# WP2F: execution contract prerequisites, not execution attestation.
WP2F_TOOL = ROOT / 'tools/check_anchor_integrity_execution_contract_v0_1.py'
WP2F_DEMO = ROOT / 'examples/anchor_integrity_v0_1/wp2f_execution_contract'
WP2F_PATHS = {'input':'input.json','carriers':'carriers.json','record_set':'record-set.json',
             'signatures':'signatures.json','trust_policy':'policy.json',
             'request':'execution/request.json','receipt':'execution/receipt.json'}
WP2F_PINS = {'input': 'd7d16dfccf2dce237060e6b77fbb7da907227b1bd56f1275cfb623ce81cd59a8', 'carriers': '70a4d15ee35db21a605ef283c531724d921658fa8bc46ca68f6867925b2c91c4', 'record_set': '232d6a0c0ddaed97f6d9a4f175f3105a45a5edc5c105fff1c04111884c7b4756', 'signatures': '5773836e21bd75b543a20acd42d5207e360486cf16330da96d4370a19348c07a', 'trust_policy': 'c49350c60de03b58e2ce10579ac9b8013665e5d4ad7c1f91ba158e5c7add970f', 'request': 'ebcc2dbee3f1b70f9715de82ec04ce607902a2974b30daa27475419295f2ac6a', 'receipt': 'fe766b25a1d9e520844dce3ef43ec1f1275407ba878e3738bb11811a0711222c'}
WP2F_ID = 'synthetic-execution-001'
WP2F_CHALLENGE = '15' * 32


def _wp2f_module():
    spec = _wp2c_importlib.spec_from_file_location('wp2f_test_checker', WP2F_TOOL)
    module = _wp2c_importlib.module_from_spec(spec)
    old = _wp2c_sys.dont_write_bytecode
    _wp2c_sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        _wp2c_sys.dont_write_bytecode = old
    return module


def _wp2f_fixture(tmp_path):
    root = tmp_path / 'execution-contract'
    _wp2c_shutil.copytree(WP2F_DEMO, root)
    return root / 'bundle', root / 'trust'


def _wp2f_pins(pair):
    b, t = pair
    return {k:_wp2c_hash((t if k == 'trust_policy' else b)/v)
            for k,v in WP2F_PATHS.items()}


def _wp2f_run(pair=None, pins=None, module=None, **kwargs):
    b, t = pair or (WP2F_DEMO/'bundle', WP2F_DEMO/'trust')
    m = module or _wp2f_module()
    options = dict(paths=dict(WP2F_PATHS), expected_digests=pins or dict(WP2F_PINS),
                   trust_root=t, binding_profile='wp2b-json-pointer-v1',
                   signature_profile='pinned-ed25519-record-signers-v1', trust_domain='TEST',
                   verification_time_epoch=WP2E_EPOCH, execution_profile=m.PROFILE,
                   record_id='synthetic-record-1', execution_id=WP2F_ID, challenge=WP2F_CHALLENGE)
    options.update(kwargs)
    return m.check_execution_contract(b, **options)


def _wp2f_write(pair, name, value):
    _wp2c_write(pair[0], 'execution/' + name, value)


def _wp2f_load(pair, name):
    return load_json(pair[0] / 'execution' / name)


def _wp2f_rehash(pair, sync_output_request=False):
    """Refresh only outer contract links, not record statements or input claims."""
    b, _ = pair
    qh = _wp2c_hash(b/'execution/request.json')
    if sync_output_request:
        output = _wp2f_load(pair, 'stdout.json')
        output['request_sha256'] = qh
        _wp2f_write(pair, 'stdout.json', output)
    receipt = _wp2f_load(pair, 'receipt.json')
    receipt['request_sha256'] = qh
    for k in ('stdout','stderr'):
        path = b / receipt[k]['path']
        if path.is_file() and not path.is_symlink():
            receipt[k].update(sha256=_wp2c_hash(path),size_bytes=path.stat().st_size)
    _wp2f_write(pair, 'receipt.json', receipt)
    return _wp2f_pins(pair)


def _wp2f_limits(report):
    assert report['candidate_status'] == 'diagnostic_only'
    assert report['authority_effect'] == 'none'
    for k in ('release_authority_activation','requested_checks_complete',
              'accepted_as_execution_evidence','accepted_as_semantic_support',
              'accepted_as_independent_anchor'):
        assert report[k] is False
    for value in report['unperformed_checks'].values():
        assert value['status'] == 'not_run' and value['result'] is None and value['reason']
    m = _wp2f_module(); sig = m.load_signature_checker(); base = sig.load_record_checker().load_binding_checker()
    m.ExecutionSchemas(base).validate('contract_report', report)


def _wp2f_has(report, code):
    return any(i['code'] == code for i in report['issues'])


@pytest.mark.parametrize('role', ('request','receipt','result','contract_report'))
def test_wp2f_schemas_are_closed_and_valid(role):
    m = _wp2f_module(); schema = load_json(SCHEMA_DIR/m.SCHEMAS[role])
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema['additionalProperties'] is False
    assert '$ref' not in json.dumps(schema)


def test_wp2f_synthetic_contract_matches_without_claiming_a_real_execution():
    assert _wp2f_pins((WP2F_DEMO/'bundle',WP2F_DEMO/'trust')) == WP2F_PINS
    r = _wp2f_run()
    assert r['status'] == 'LOCAL_EXECUTION_CONTRACT_CONSISTENT'
    assert r['signature_check']['status'] == 'LOCAL_RECORD_SIGNATURES_VERIFIED'
    assert r['signature_check']['signer_result'] == 'test_key_signatures_verified'
    assert len(r['checked_objects']) == 9
    assert r['receipt_declaration']['observation_basis'] == 'synthetic_fixture'
    assert r['receipt_declaration']['recorded_result']['result'] == 'unresolved'
    _wp2f_limits(r)


@pytest.mark.parametrize('role,name', [('request','request.json'),('receipt','receipt.json'),('result','stdout.json')])
@pytest.mark.parametrize('mutation', ['extra','authority','promotion','wrong_version'])
def test_wp2f_contract_schema_rejects_promotions(role,name,mutation):
    m = _wp2f_module(); d = load_json(WP2F_DEMO/'bundle/execution'/name)
    if mutation=='extra': d['unreviewed'] = True
    elif mutation=='authority': d['authority_effect'] = 'release'
    elif mutation=='promotion': d['release_authority_activation'] = True
    else: d['schema_version'] = 'other'
    assert_invalid(m.SCHEMAS[role],d)


@pytest.mark.parametrize('role,name', [('request','request.json'),('receipt','receipt.json'),('result','stdout.json')])
def test_wp2f_every_required_field_is_required(role,name):
    m = _wp2f_module(); d = load_json(WP2F_DEMO/'bundle/execution'/name)
    schema = load_json(SCHEMA_DIR/m.SCHEMAS[role])
    for field in schema['required']:
        v = deepcopy(d); del v[field]
        assert_invalid(m.SCHEMAS[role],v)


@pytest.mark.parametrize('role', list(WP2F_PATHS))
@pytest.mark.parametrize('value', ['0'*64,'bad',None])
def test_wp2f_all_seven_external_pins_are_required_and_checked(role,value):
    pins = dict(WP2F_PINS); pins[role] = value
    r = _wp2f_run(pins=pins)
    assert r['status'] == 'LOCAL_EXECUTION_CONTRACT_INVALID'
    _wp2f_limits(r)


@pytest.mark.parametrize('name', ['execution/request.json','execution/receipt.json','execution/stdout.json',
    'execution/stderr.txt','execution/verifier.source.txt','execution/runtime.json','execution/claim.txt',
    'execution/evidence.bin','execution/source.bin','signature-1.json','record-1.json','source.json'])
def test_wp2f_missing_required_material_never_succeeds(tmp_path,name):
    pair = _wp2f_fixture(tmp_path); (pair[0]/name).unlink()
    r = _wp2f_run(pair)
    assert r['status'] == 'LOCAL_EXECUTION_CONTRACT_INCOMPLETE'
    _wp2f_limits(r)


@pytest.mark.parametrize('name', ['execution/request.json','execution/receipt.json','execution/stdout.json',
    'execution/stderr.txt','execution/verifier.source.txt','execution/runtime.json','execution/claim.txt',
    'execution/evidence.bin','execution/source.bin','signature-1.json','record-1.json'])
def test_wp2f_tampered_raw_bytes_are_rejected(tmp_path,name):
    pair = _wp2f_fixture(tmp_path); p = pair[0]/name; p.write_bytes(p.read_bytes()+b' ')
    r = _wp2f_run(pair)
    assert r['status'] == 'LOCAL_EXECUTION_CONTRACT_INVALID'
    _wp2f_limits(r)


@pytest.mark.parametrize('field', ['execution_id','challenge','subject','verifier','binding'])
def test_wp2f_rehashed_request_identity_substitutions_fail(tmp_path,field):
    pair = _wp2f_fixture(tmp_path); q = _wp2f_load(pair,'request.json')
    if field == 'execution_id': q[field]='different'
    elif field == 'challenge': q[field]='ab'*32
    elif field == 'subject': q[field]['run_id']='other-run'
    elif field == 'verifier': q[field]['method_version']='999'
    else: q[field]['claim_id']='different-claim'
    _wp2f_write(pair,'request.json',q)
    r = _wp2f_run(pair,_wp2f_rehash(pair,True))
    assert r['status'] == 'LOCAL_EXECUTION_CONTRACT_INVALID'


@pytest.mark.parametrize('field', ['record_binding','request_sha256','execution_id','challenge','subject',
    'verifier','entrypoint_sha256','runtime_manifest_sha256','input_sha256','invocation'])
def test_wp2f_rehashed_receipt_substitutions_fail(tmp_path,field):
    pair = _wp2f_fixture(tmp_path); r = _wp2f_load(pair,'receipt.json')
    if field=='record_binding':r[field]['sha256']='00'*32
    elif field in ('request_sha256','entrypoint_sha256','runtime_manifest_sha256','challenge'):r[field]='ab'*32
    elif field=='execution_id':r[field]='different'
    elif field=='subject':r[field]['run_id']=None
    elif field=='verifier':r[field]['method_id']='different'
    elif field=='input_sha256':r[field]['evidence_content']='00'*32
    else:r[field]['argv'].append('unexpected')
    _wp2f_write(pair,'receipt.json',r)
    result=_wp2f_run(pair,_wp2f_pins(pair)); assert result['status']=='LOCAL_EXECUTION_CONTRACT_INVALID'


@pytest.mark.parametrize('role', ['claim_text','evidence_content','source_content'])
def test_wp2f_rehashed_process_input_cannot_replace_signed_input(tmp_path,role):
    pair=_wp2f_fixture(tmp_path);q=_wp2f_load(pair,'request.json');r=_wp2f_load(pair,'receipt.json')
    p=pair[0]/q['inputs'][role]['path'];p.write_bytes(b'replacement')
    q['inputs'][role].update(sha256=_wp2c_hash(p),size_bytes=p.stat().st_size)
    r['input_sha256'][role]=_wp2c_hash(p)
    _wp2f_write(pair,'request.json',q);_wp2f_write(pair,'receipt.json',r)
    result=_wp2f_run(pair,_wp2f_rehash(pair,True))
    assert result['status']=='LOCAL_EXECUTION_CONTRACT_INVALID'
    assert _wp2f_has(result,'execution_input_'+role+'_mismatch')


def test_wp2f_rehashed_source_identity_must_match_signed_verifier(tmp_path):
    pair=_wp2f_fixture(tmp_path);q=_wp2f_load(pair,'request.json');r=_wp2f_load(pair,'receipt.json')
    p=pair[0]/q['entrypoint']['path'];p.write_bytes(b'other source')
    q['entrypoint'].update(sha256=_wp2c_hash(p),size_bytes=p.stat().st_size)
    r['entrypoint_sha256']=_wp2c_hash(p)
    _wp2f_write(pair,'request.json',q);_wp2f_write(pair,'receipt.json',r)
    result=_wp2f_run(pair,_wp2f_rehash(pair,True))
    assert _wp2f_has(result,'entrypoint_identity_mismatch')


@pytest.mark.parametrize('field', ['execution_id','challenge','request_sha256','subject','verifier','binding','verification'])
def test_wp2f_rehashed_stdout_must_match_request_and_signed_record(tmp_path,field):
    pair=_wp2f_fixture(tmp_path);out=_wp2f_load(pair,'stdout.json')
    if field=='execution_id':out[field]='other'
    elif field in ('challenge','request_sha256'):out[field]='00'*32
    elif field=='subject':out[field]['run_id']='other'
    elif field=='verifier':out[field]['method_version']='2'
    elif field=='binding':out[field]['source_id']='other'
    else:out[field]['result']='supported'
    _wp2f_write(pair,'stdout.json',out)
    r=_wp2f_run(pair,_wp2f_rehash(pair));assert r['status']=='LOCAL_EXECUTION_CONTRACT_INVALID'


@pytest.mark.parametrize('state,code,duration', [('failed',1,1),('timed_out',None,1001),('not_started',None,None)])
def test_wp2f_noncompleted_receipt_never_admits_execution(tmp_path,state,code,duration):
    pair=_wp2f_fixture(tmp_path);r=_wp2f_load(pair,'receipt.json')
    r['process'].update(state=state,exit_code=code,duration_ms=duration)
    _wp2f_write(pair,'receipt.json',r)
    result=_wp2f_run(pair,_wp2f_pins(pair))
    assert result['status']=='LOCAL_EXECUTION_CONTRACT_INCOMPLETE'
    assert result['receipt_declaration']['recorded_result'] is None
    _wp2f_limits(result)


@pytest.mark.parametrize('stream',['stdout','stderr'])
def test_wp2f_truncated_stream_never_counts_as_complete(tmp_path,stream):
    pair=_wp2f_fixture(tmp_path);r=_wp2f_load(pair,'receipt.json')
    r['process'][stream+'_complete']=False;_wp2f_write(pair,'receipt.json',r)
    result=_wp2f_run(pair,_wp2f_pins(pair))
    assert result['status']=='LOCAL_EXECUTION_CONTRACT_INCOMPLETE'
    assert _wp2f_has(result,'recorded_stream_incomplete')


@pytest.mark.parametrize('field,value',[('exit_code',1),('exit_code',None),('duration_ms',None),('duration_ms',-1),('state','attested')])
def test_wp2f_inconsistent_terminal_declarations_are_invalid(tmp_path,field,value):
    pair=_wp2f_fixture(tmp_path);r=_wp2f_load(pair,'receipt.json');r['process'][field]=value
    _wp2f_write(pair,'receipt.json',r)
    result=_wp2f_run(pair,_wp2f_pins(pair));assert result['status']=='LOCAL_EXECUTION_CONTRACT_INVALID'


@pytest.mark.parametrize('field,value', [('duration_ms',1001),('duration_ms',100000)])
def test_wp2f_completed_duration_must_fit_request(tmp_path,field,value):
    pair=_wp2f_fixture(tmp_path);r=_wp2f_load(pair,'receipt.json');r['process'][field]=value
    _wp2f_write(pair,'receipt.json',r)
    result=_wp2f_run(pair,_wp2f_pins(pair));assert _wp2f_has(result,'recorded_duration_exceeds_limit')


@pytest.mark.parametrize('path',['../outside','/tmp/outside','./x','x//y','a/../b','x\\y','a.','https://example.invalid/x'])
def test_wp2f_unsafe_material_paths_are_rejected(tmp_path,path):
    pair=_wp2f_fixture(tmp_path);q=_wp2f_load(pair,'request.json');q['entrypoint']['path']=path
    _wp2f_write(pair,'request.json',q)
    r=_wp2f_run(pair,_wp2f_rehash(pair,True));assert r['status']=='LOCAL_EXECUTION_CONTRACT_INVALID'


@pytest.mark.parametrize('path',['input.json','record-1.json','signature-1.json','execution/request.json',
                                'execution/receipt.json','execution/stdout.json','execution/claim.txt'])
def test_wp2f_cross_role_reuse_is_invalid(tmp_path,path):
    pair=_wp2f_fixture(tmp_path);q=_wp2f_load(pair,'request.json');q['entrypoint']['path']=path
    _wp2f_write(pair,'request.json',q)
    r=_wp2f_run(pair,_wp2f_rehash(pair,True));assert r['status']=='LOCAL_EXECUTION_CONTRACT_INVALID'


@pytest.mark.parametrize('kind',['symlink','hardlink','fifo'])
def test_wp2f_linked_or_special_material_is_not_admitted(tmp_path,kind):
    import os
    pair=_wp2f_fixture(tmp_path);p=pair[0]/'execution/verifier.source.txt';raw=p.read_bytes();p.unlink()
    other=tmp_path/'outside';other.write_bytes(raw)
    if kind=='symlink':p.symlink_to(other)
    elif kind=='hardlink':os.link(other,p)
    else:os.mkfifo(p)
    r=_wp2f_run(pair);assert r['status']=='LOCAL_EXECUTION_CONTRACT_INVALID'


@pytest.mark.parametrize('name',['request.json','receipt.json','stdout.json'])
def test_wp2f_duplicate_json_keys_rejected_after_repin(tmp_path,name):
    pair=_wp2f_fixture(tmp_path);p=pair[0]/'execution'/name
    raw=p.read_bytes();p.write_bytes(raw.replace(b'{',b'{"authority_effect":"none",',1))
    if name=='stdout.json':pins=_wp2f_rehash(pair)
    else:pins=_wp2f_pins(pair)
    r=_wp2f_run(pair,pins);assert r['status']=='LOCAL_EXECUTION_CONTRACT_INVALID'


def test_wp2f_unattested_observer_label_does_not_become_attestation(tmp_path):
    pair=_wp2f_fixture(tmp_path);r=_wp2f_load(pair,'receipt.json')
    r['observation_basis']='unattested_observer_statement';r['observer']['observer_id']='claimed-institution'
    _wp2f_write(pair,'receipt.json',r)
    result=_wp2f_run(pair,_wp2f_pins(pair))
    assert result['status']=='LOCAL_EXECUTION_CONTRACT_CONSISTENT'
    _wp2f_limits(result)


def test_wp2f_bad_record_signature_blocks_execution_comparison(tmp_path):
    pair=_wp2f_fixture(tmp_path);s=load_json(pair[0]/'signature-1.json')
    s['signature_hex']='00'*64;_wp2c_write(pair[0],'signature-1.json',s)
    _wp2e_refresh_envelope_manifest(pair)
    result=_wp2f_run(pair,_wp2f_pins(pair))
    assert result['status']=='LOCAL_EXECUTION_CONTRACT_INVALID'
    assert result['receipt_declaration'] is None
    assert len(result['checked_objects'])==2


def test_wp2f_argv_is_inert_data_and_cannot_execute_artifact_code(tmp_path):
    pair=_wp2f_fixture(tmp_path);q=_wp2f_load(pair,'request.json');r=_wp2f_load(pair,'receipt.json')
    marker=tmp_path/'EXECUTED'
    q['invocation']['argv']=['/bin/sh','-c','touch '+str(marker)]
    r['invocation']=deepcopy(q['invocation'])
    _wp2f_write(pair,'request.json',q);_wp2f_write(pair,'receipt.json',r)
    result=_wp2f_run(pair,_wp2f_rehash(pair,True))
    assert result['status']=='LOCAL_EXECUTION_CONTRACT_CONSISTENT'
    assert not marker.exists();_wp2f_limits(result)


@pytest.mark.parametrize('field',['accepted_as_execution_evidence','accepted_as_semantic_support',
                                  'accepted_as_independent_anchor','requested_checks_complete','release_authority_activation'])
def test_wp2f_report_cannot_promote_authority(field):
    r=_wp2f_run();r[field]=True
    assert_invalid('anchor_integrity_execution_contract_report_v0_1.schema.json',r)


@pytest.mark.parametrize('check',_wp2f_module().UNPERFORMED)
def test_wp2f_report_cannot_promote_unperformed_checks(check):
    r=_wp2f_run();r['unperformed_checks'][check].update(status='completed',result='verified')
    assert_invalid('anchor_integrity_execution_contract_report_v0_1.schema.json',r)


def test_wp2f_schema_rejects_success_with_noncompleted_process_or_missing_checks():
    r=_wp2f_run()
    for mode in ('process','signature','objects','issue','contract','result'):
        v=deepcopy(r)
        if mode=='process':v['receipt_declaration']['process']['stdout_complete']=False
        elif mode=='signature':v['signature_check']['status']=None
        elif mode=='objects':v['checked_objects']=[]
        elif mode=='issue':v['issues']=[{'code':'x','object_id':'x','severity':'incomplete'}]
        elif mode=='contract':v['contract_check']=_wp2f_module().not_run()
        else:v['receipt_declaration']['recorded_result']=None
        assert_invalid('anchor_integrity_execution_contract_report_v0_1.schema.json',v)


def test_wp2f_repeated_checks_do_not_change_inputs_and_are_deterministic(tmp_path):
    pair=_wp2f_fixture(tmp_path)
    before={str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    a=_wp2f_run(pair);b=_wp2f_run(pair)
    assert a==b
    assert before=={str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def _wp2f_cli():
    m=_wp2f_module()
    cmd=[_wp2c_sys.executable,str(WP2F_TOOL),'--bundle-root',str(WP2F_DEMO/'bundle'),
         '--trust-root',str(WP2F_DEMO/'trust')]
    for k,v in WP2F_PATHS.items():cmd += ['--'+k.replace('_','-'),v,'--expected-'+k.replace('_','-')+'-sha256',WP2F_PINS[k]]
    cmd += ['--binding-profile','wp2b-json-pointer-v1','--signature-profile','pinned-ed25519-record-signers-v1',
            '--execution-profile',m.PROFILE,'--trust-domain','TEST','--verification-time-epoch',str(WP2E_EPOCH),
            '--record-id','synthetic-record-1','--execution-id',WP2F_ID,'--challenge',WP2F_CHALLENGE]
    return cmd


def test_wp2f_real_cli_reports_only_contract_consistency():
    p=_wp2c_subprocess.run(_wp2f_cli(),capture_output=True,timeout=45)
    assert p.returncode==0,p.stderr
    r=json.loads(p.stdout);assert r['status']=='LOCAL_EXECUTION_CONTRACT_CONSISTENT';_wp2f_limits(r)


def test_wp2f_unknown_cli_profile_emits_no_success_report():
    cmd=_wp2f_cli();cmd[cmd.index('--execution-profile')+1]='unknown'
    p=_wp2c_subprocess.run(cmd,capture_output=True,timeout=30)
    assert p.returncode==2 and not p.stdout


def test_wp2f_missing_backend_cannot_become_a_reported_success(monkeypatch):
    m=_wp2f_module();sig=m.load_signature_checker()
    def fail():raise RuntimeError('missing_test_backend')
    monkeypatch.setattr(sig,'OpenSSLVerifier',fail);monkeypatch.setattr(m,'load_signature_checker',lambda:sig)
    with pytest.raises(RuntimeError):_wp2f_run(module=m)


def test_wp2f_registration_uses_existing_module_without_manifest_changes():
    for name in ('ci/tools-tests.list','ci/pytest-tests.list'):
        assert _manifest_entries(ROOT/name).count(TEST_PATH)==1




# WP2G: distinct observer-policy receipt signatures; never execution admission.
WP2G_TOOL = ROOT / 'tools/check_anchor_integrity_receipt_signatures_v0_1.py'
WP2G_DEMO = ROOT / 'examples/anchor_integrity_v0_1/wp2g_receipt_signatures'
WP2G_PATHS = {**WP2F_PATHS, 'observer_policy':'policy.json',
              'receipt_signature':'execution/receipt-signature.json'}
WP2G_OBSERVER = 'synthetic-observer-NOT-EXECUTED'
# RFC 8032 test 1: PUBLIC TEST material, distinct from the verifier's test-2 key.
WP2G_SEED = bytes.fromhex('9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60')
WP2G_PINS = {'input': 'd7d16dfccf2dce237060e6b77fbb7da907227b1bd56f1275cfb623ce81cd59a8', 'carriers': '70a4d15ee35db21a605ef283c531724d921658fa8bc46ca68f6867925b2c91c4', 'record_set': '232d6a0c0ddaed97f6d9a4f175f3105a45a5edc5c105fff1c04111884c7b4756', 'signatures': '5773836e21bd75b543a20acd42d5207e360486cf16330da96d4370a19348c07a', 'trust_policy': 'c49350c60de03b58e2ce10579ac9b8013665e5d4ad7c1f91ba158e5c7add970f', 'request': 'ebcc2dbee3f1b70f9715de82ec04ce607902a2974b30daa27475419295f2ac6a', 'receipt': 'fe766b25a1d9e520844dce3ef43ec1f1275407ba878e3738bb11811a0711222c', 'observer_policy': 'e0168bb0d71baaf65077b89752af853b5f003dc63dccb6e943e29b93e98def55', 'receipt_signature': '38d64ec24c866c774f3ddaff85d20996cbcb8599b9290a563e9938de3edd6499'}


def _wp2g_module():
    spec = _wp2c_importlib.spec_from_file_location('wp2g_test_checker', WP2G_TOOL)
    module = _wp2c_importlib.module_from_spec(spec)
    old = _wp2c_sys.dont_write_bytecode
    _wp2c_sys.dont_write_bytecode = True
    try: spec.loader.exec_module(module)
    finally: _wp2c_sys.dont_write_bytecode = old
    return module


def _wp2g_fixture(tmp_path):
    root=tmp_path/'receipt-signatures';_wp2c_shutil.copytree(WP2G_DEMO,root)
    return root/'bundle',root/'trust',root/'observer-trust'


def _wp2g_path(roots,role):
    b,t,o=roots
    return (t if role=='trust_policy' else o if role=='observer_policy' else b)/WP2G_PATHS[role]


def _wp2g_pins(roots):
    return {k:_wp2c_hash(_wp2g_path(roots,k)) for k in WP2G_PATHS}


def _wp2g_run(roots=None,pins=None,module=None,**kwargs):
    roots=roots or (WP2G_DEMO/'bundle',WP2G_DEMO/'trust',WP2G_DEMO/'observer-trust')
    b,t,o=roots;m=module or _wp2g_module()
    options=dict(paths=dict(WP2G_PATHS),expected_digests=pins or dict(WP2G_PINS),trust_root=t,
                 observer_trust_root=o,binding_profile='wp2b-json-pointer-v1',
                 signature_profile='pinned-ed25519-record-signers-v1',execution_profile='single-record-execution-contract-v1',
                 receipt_signature_profile=m.PROFILE,trust_domain='TEST',verification_time_epoch=WP2E_EPOCH,
                 record_id='synthetic-record-1',execution_id=WP2F_ID,challenge=WP2F_CHALLENGE,observer_id=WP2G_OBSERVER)
    options.update(kwargs)
    return m.check_receipt_signature(b,**options)


def _wp2g_resign(roots,sign=True,seed=WP2G_SEED):
    b,t,o=roots;m=_wp2g_module();p=load_json(o/'policy.json');s=load_json(b/'execution/receipt-signature.json')
    s.update(observer_policy_sha256=_wp2c_hash(o/'policy.json'),record_signer_policy_sha256=_wp2c_hash(t/'policy.json'),
             receipt_sha256=_wp2c_hash(b/'execution/receipt.json'),key_id=p['keys'][0]['key_id'])
    if sign:
        s['signature_hex']=_wp2e_sign(m.signing_bytes(s['observer_policy_sha256'],s['record_signer_policy_sha256'],
                                       s['key_id'],(b/'execution/receipt.json').read_bytes()),seed=seed).hex()
    _wp2c_write(b,'execution/receipt-signature.json',s)
    return _wp2g_pins(roots)


def _wp2g_has(r,code):
    return any(i['code']==code for i in r['issues'])


def _wp2g_limits(r):
    assert r['candidate_status']=='diagnostic_only' and r['authority_effect']=='none'
    for k in ('release_authority_activation','requested_checks_complete','accepted_as_execution_evidence',
              'accepted_as_semantic_support','accepted_as_independent_anchor'):assert r[k] is False
    for c in r['unperformed_checks'].values():assert c['status']=='not_run' and c['result'] is None and c['reason']
    m=_wp2g_module();base=m.load_execution_checker().load_signature_checker().load_record_checker().load_binding_checker()
    m.ReceiptSchemas(base).validate('report',r)


def test_wp2g_real_signature_demo_has_distinct_role_and_no_execution_admission():
    roots=(WP2G_DEMO/'bundle',WP2G_DEMO/'trust',WP2G_DEMO/'observer-trust')
    assert _wp2g_pins(roots)==WP2G_PINS
    r=_wp2g_run();assert r['status']=='LOCAL_RECEIPT_SIGNATURE_VERIFIED',r['issues']
    assert r['authenticated_receipt_statement'] is True
    assert r['observer_statement_authentication']['result']=='test_key_receipt_signature_verified'
    assert r['receipt_signature_check']['result']=='valid'
    assert r['execution_contract_check']['status']=='LOCAL_EXECUTION_CONTRACT_CONSISTENT'
    assert r['execution_contract_check']['checked_object_count']==9
    assert r['observation_basis']=='synthetic_fixture'
    assert r['observed_digests']==r['expected_digests']==WP2G_PINS
    _wp2g_limits(r)


def test_wp2g_original_wp2f_example_bytes_are_not_relabelled():
    for p in WP2F_DEMO.rglob('*'):
        if p.is_file():assert p.read_bytes()==(WP2G_DEMO/p.relative_to(WP2F_DEMO)).read_bytes()
    record=load_json(WP2G_DEMO/'trust/policy.json');observer=load_json(WP2G_DEMO/'observer-trust/policy.json')
    assert not ({k['public_key_hex'] for k in record['keys']}&{k['public_key_hex'] for k in observer['keys']})


@pytest.mark.parametrize('role',list(WP2G_PATHS))
def test_wp2g_each_external_digest_pin_is_enforced(role):
    pins=dict(WP2G_PINS);pins[role]='0'*64
    r=_wp2g_run(pins=pins);assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INVALID';_wp2g_limits(r)


@pytest.mark.parametrize('role',list(WP2G_PATHS))
def test_wp2g_each_required_file_is_missing_not_verified(tmp_path,role):
    roots=_wp2g_fixture(tmp_path);_wp2g_path(roots,role).unlink()
    r=_wp2g_run(roots);assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INCOMPLETE';_wp2g_limits(r)


@pytest.mark.parametrize('role',['observer_policy','receipt_signature'])
@pytest.mark.parametrize('raw',[b'{"x":1,"x":2}',b'{"x":NaN}',b'\xff',b'{} trailing',b'[]',b'null'])
def test_wp2g_strict_json_for_new_roles(tmp_path,role,raw):
    roots=_wp2g_fixture(tmp_path);_wp2g_path(roots,role).write_bytes(raw)
    r=_wp2g_run(roots,_wp2g_pins(roots));assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INVALID';_wp2g_limits(r)


@pytest.mark.parametrize('role,limit',[('observer_policy',262144),('receipt_signature',16384)])
def test_wp2g_new_artifacts_have_resource_limits(tmp_path,role,limit):
    roots=_wp2g_fixture(tmp_path);_wp2g_path(roots,role).write_bytes(b' '*(limit+1))
    r=_wp2g_run(roots,_wp2g_pins(roots));assert _wp2g_has(r,role+'_size_limit');_wp2g_limits(r)


@pytest.mark.parametrize('field,value',[
 ('purpose','verifier_record_statement'),('signature_suite','none'),('public_key_hex','FF'*32),
 ('public_key_sha256','0'*64),('state','revoked'),('not_before_epoch',WP2E_EPOCH+1),
 ('not_after_epoch',WP2E_EPOCH),('relation_types',['contradicts']),('results',['supported']),
 ('observation_bases',['unattested_observer_statement']),('executable','evil.py')])
def test_wp2g_key_permissions_and_states_are_not_interchangeable(tmp_path,field,value):
    roots=_wp2g_fixture(tmp_path);p=load_json(roots[2]/'policy.json');p['keys'][0][field]=value
    _wp2c_write(roots[2],'policy.json',p)
    r=_wp2g_run(roots,_wp2g_resign(roots));assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INVALID';_wp2g_limits(r)


@pytest.mark.parametrize('field,value',[('verifier_id','other'),('method_id','other'),('method_version','2'),('implementation_sha256','0'*64)])
def test_wp2g_verifier_tuple_scope_is_exact(tmp_path,field,value):
    roots=_wp2g_fixture(tmp_path);p=load_json(roots[2]/'policy.json');p['keys'][0]['verifier'][field]=value
    _wp2c_write(roots[2],'policy.json',p)
    r=_wp2g_run(roots,_wp2g_resign(roots));assert _wp2g_has(r,'observer_verifier_scope_mismatch');_wp2g_limits(r)


@pytest.mark.parametrize('where,field,value',[
 ('subject','subject_id','other'),('subject','run_id',None),('observer','observer_id','other'),
 ('observer','implementation_sha256','0'*64),('execution_scope','record_id','other'),
 ('execution_scope','execution_id','other'),('execution_scope','challenge','0'*64),
 ('execution_scope','request_sha256','0'*64)])
def test_wp2g_observer_subject_and_execution_scopes_are_exact(tmp_path,where,field,value):
    roots=_wp2g_fixture(tmp_path);p=load_json(roots[2]/'policy.json');p[where][field]=value
    _wp2c_write(roots[2],'policy.json',p)
    r=_wp2g_run(roots,_wp2g_resign(roots));assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INVALID';_wp2g_limits(r)


@pytest.mark.parametrize('field,value',[('trust_domain','OPERATOR'),('record_signer_policy_sha256','0'*64),
 ('key_separation','same_key_allowed'),('authority_effect','release'),('release_authority_activation',True),
 ('candidate_status','active'),('profile','auto')])
def test_wp2g_policy_cannot_widen_trust_or_authority(tmp_path,field,value):
    roots=_wp2g_fixture(tmp_path);p=load_json(roots[2]/'policy.json');p[field]=value
    _wp2c_write(roots[2],'policy.json',p)
    r=_wp2g_run(roots,_wp2g_resign(roots));assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INVALID';_wp2g_limits(r)


@pytest.mark.parametrize('kind',['duplicate_id','duplicate_material','empty','over_limit','invalid_interval','record_key'])
def test_wp2g_policy_key_inventory_constraints(tmp_path,kind):
    roots=_wp2g_fixture(tmp_path);p=load_json(roots[2]/'policy.json');k=deepcopy(p['keys'][0])
    if kind=='duplicate_id':p['keys'].append(k)
    elif kind=='duplicate_material':k['key_id']='alias';p['keys'].append(k)
    elif kind=='empty':p['keys']=[]
    elif kind=='over_limit':p['keys']=[k]*65
    elif kind=='invalid_interval':p['keys'][0]['not_before_epoch']=p['keys'][0]['not_after_epoch']
    else:
        v=load_json(roots[1]/'policy.json')['keys'][0]
        p['keys'][0].update(public_key_hex=v['public_key_hex'],public_key_sha256=v['public_key_sha256'])
    _wp2c_write(roots[2],'policy.json',p)
    # Empty policies are malformed; no signing helper can select an empty key list.
    pins=_wp2g_pins(roots) if kind=='empty' else _wp2g_resign(roots,seed=WP2E_SEED if kind=='record_key' else WP2G_SEED)
    r=_wp2g_run(roots,pins);assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INVALID';_wp2g_limits(r)
    if kind=='record_key':assert _wp2g_has(r,'observer_key_reuses_verifier_key')


@pytest.mark.parametrize('field,value',[('signature_suite','rsa'),('signature_domain','PULSEMECH-ANCHOR-RECORD-SIGNATURE-V1'),
 ('public_key_hex','0'*64),('command','evil.py'),('signed_message','invented'),('observer_id','other'),
 ('execution_id','other'),('record_id','other'),('receipt_sha256','0'*64),('observer_policy_sha256','0'*64),
 ('record_signer_policy_sha256','0'*64),('key_id','unknown'),('release_authority_activation',True),
 ('authority_effect','release'),('accepted_as_execution_evidence',True)])
def test_wp2g_signature_envelope_substitutions_rejected(tmp_path,field,value):
    roots=_wp2g_fixture(tmp_path);s=load_json(_wp2g_path(roots,'receipt_signature'));s[field]=value
    _wp2c_write(roots[0],WP2G_PATHS['receipt_signature'],s)
    r=_wp2g_run(roots,_wp2g_pins(roots));assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INVALID';_wp2g_limits(r)


@pytest.mark.parametrize('sig',['0'*128,'ff'*64,'A'*128,'a'*127,'x'*128])
def test_wp2g_bad_signature_cannot_pass(tmp_path,sig):
    roots=_wp2g_fixture(tmp_path);s=load_json(_wp2g_path(roots,'receipt_signature'));s['signature_hex']=sig
    _wp2c_write(roots[0],WP2G_PATHS['receipt_signature'],s)
    r=_wp2g_run(roots,_wp2g_pins(roots));assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INVALID';_wp2g_limits(r)


@pytest.mark.parametrize('which',['receipt_whitespace','receipt_duration','policy_whitespace','policy_id','key_id'])
def test_wp2g_rehashing_outer_artifacts_cannot_replace_the_observer_signature(tmp_path,which):
    roots=_wp2g_fixture(tmp_path);b,t,o=roots
    if which=='receipt_whitespace':
        p=b/'execution/receipt.json';p.write_bytes(b' '+p.read_bytes())
    elif which=='receipt_duration':
        r=load_json(b/'execution/receipt.json');r['process']['duration_ms']=2;_wp2c_write(b,'execution/receipt.json',r)
    elif which=='policy_whitespace':
        p=o/'policy.json';p.write_bytes(b' '+p.read_bytes())
    else:
        p=load_json(o/'policy.json')
        if which=='policy_id':p['policy_id']='renamed-policy'
        else:p['keys'][0]['key_id']='renamed-key'
        _wp2c_write(o,'policy.json',p)
    r=_wp2g_run(roots,_wp2g_resign(roots,sign=False))
    assert _wp2g_has(r,'execution_receipt_signature_invalid'),r['issues']
    assert r['observer_key_authorization']['result']=='authorized'
    assert r['receipt_signature_check']['result']=='invalid';_wp2g_limits(r)


def test_wp2g_record_signature_cannot_be_reused_as_receipt_signature(tmp_path):
    roots=_wp2g_fixture(tmp_path);s=load_json(_wp2g_path(roots,'receipt_signature'))
    s['signature_hex']=load_json(roots[0]/'signature-1.json')['signature_hex']
    _wp2c_write(roots[0],WP2G_PATHS['receipt_signature'],s)
    r=_wp2g_run(roots,_wp2g_pins(roots));assert _wp2g_has(r,'execution_receipt_signature_invalid');_wp2g_limits(r)


def test_wp2g_different_signing_domain_cannot_authenticate_same_receipt(tmp_path):
    roots=_wp2g_fixture(tmp_path);s=load_json(_wp2g_path(roots,'receipt_signature'));m=_wp2e_module()
    s['signature_hex']=_wp2e_sign(m.signing_bytes(WP2G_PINS['observer_policy'],s['key_id'],
                                      _wp2g_path(roots,'receipt').read_bytes()),seed=WP2G_SEED).hex()
    _wp2c_write(roots[0],WP2G_PATHS['receipt_signature'],s)
    r=_wp2g_run(roots,_wp2g_pins(roots));assert _wp2g_has(r,'execution_receipt_signature_invalid');_wp2g_limits(r)


@pytest.mark.parametrize('before,after,expected',[(WP2E_EPOCH,WP2E_EPOCH+1,True),
 (WP2E_EPOCH-1,WP2E_EPOCH,False),(WP2E_EPOCH+1,WP2E_EPOCH+2,False)])
def test_wp2g_observer_validity_window_is_half_open(tmp_path,before,after,expected):
    roots=_wp2g_fixture(tmp_path);p=load_json(roots[2]/'policy.json');p['keys'][0].update(not_before_epoch=before,not_after_epoch=after)
    _wp2c_write(roots[2],'policy.json',p);r=_wp2g_run(roots,_wp2g_resign(roots))
    assert (r['status']=='LOCAL_RECEIPT_SIGNATURE_VERIFIED') is expected;_wp2g_limits(r)


def test_wp2g_operator_label_requires_both_explicit_policies_and_does_not_prove_identity(tmp_path):
    roots=_wp2g_fixture(tmp_path);b,t,o=roots
    for root in (t,o):
        p=load_json(root/'policy.json');p['trust_domain']='OPERATOR';_wp2c_write(root,'policy.json',p)
    # Test-only signatures over explicitly selected policies; not operational keys.
    _wp2e_resign((b,t))
    p=load_json(o/'policy.json');p['record_signer_policy_sha256']=_wp2c_hash(t/'policy.json');_wp2c_write(o,'policy.json',p)
    r=_wp2g_run(roots,_wp2g_resign(roots),trust_domain='OPERATOR')
    assert r['status']=='LOCAL_RECEIPT_SIGNATURE_VERIFIED',r['issues']
    assert r['observer_statement_authentication']['result']=='authorized_key_receipt_signature_verified'
    _wp2g_limits(r)


@pytest.mark.parametrize('state',['failed','timed_out','not_started','truncated'])
def test_wp2g_even_signed_incomplete_process_receipt_cannot_be_admitted(tmp_path,state):
    roots=_wp2g_fixture(tmp_path);r=load_json(_wp2g_path(roots,'receipt'));p=r['process']
    if state=='truncated':p['stdout_complete']=False
    elif state=='not_started':p.update(state=state,exit_code=None,duration_ms=None,stdout_complete=False,stderr_complete=False)
    elif state=='timed_out':p.update(state=state,exit_code=None,stdout_complete=False,stderr_complete=False)
    else:p.update(state=state,exit_code=1)
    _wp2c_write(roots[0],WP2G_PATHS['receipt'],r)
    result=_wp2g_run(roots,_wp2g_resign(roots))
    assert result['status']=='LOCAL_RECEIPT_SIGNATURE_INCOMPLETE',result['issues']
    assert result['receipt_signature_check']['result'] is None;_wp2g_limits(result)


def test_wp2g_completed_receipt_with_wrong_result_is_invalid_even_when_signed(tmp_path):
    roots=_wp2g_fixture(tmp_path);b,t,_=roots;s=load_json(b/'execution/stdout.json')
    s['verification']['result']='supported';_wp2c_write(b,'execution/stdout.json',s)
    _wp2f_rehash((b,t));result=_wp2g_run(roots,_wp2g_resign(roots))
    assert _wp2g_has(result,'execution.stdout_signed_record_result_mismatch');_wp2g_limits(result)


@pytest.mark.parametrize('role',['observer_policy','receipt_signature','receipt'])
@pytest.mark.parametrize('kind',['symlink','hardlink','fifo'])
def test_wp2g_unsafe_files_rejected_before_admission(tmp_path,role,kind):
    roots=_wp2g_fixture(tmp_path);p=_wp2g_path(roots,role);backup=p.with_name(p.name+'.backup');p.rename(backup)
    if kind=='symlink':p.symlink_to(backup)
    elif kind=='hardlink':_wp2_os.link(backup,p)
    else:_wp2_os.mkfifo(p)
    r=_wp2g_run(roots);assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INVALID';_wp2g_limits(r)


@pytest.mark.parametrize('role,value',[('observer_policy','../policy.json'),('receipt_signature','/tmp/receipt'),
 ('receipt_signature','execution/../receipt-signature.json'),('receipt_signature','execution/receipt.json'),
 ('receipt_signature','record-1.json'),('receipt_signature','execution/RECEIPT.json')])
def test_wp2g_unsafe_and_cross_role_paths_rejected(tmp_path,role,value):
    roots=_wp2g_fixture(tmp_path);paths=dict(WP2G_PATHS);paths[role]=value;pins=dict(WP2G_PINS)
    if value=='execution/RECEIPT.json':
        (roots[0]/value).write_bytes(_wp2g_path(roots,'receipt_signature').read_bytes())
    if value=='execution/receipt.json':pins['receipt_signature']=pins['receipt']
    if value=='record-1.json':pins['receipt_signature']=_wp2c_hash(roots[0]/value)
    r=_wp2g_run(roots,pins,paths=paths);assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INVALID';_wp2g_limits(r)


@pytest.mark.parametrize('case',['evidence','verifier_trust','parent','nested'])
def test_wp2g_policy_roots_must_be_pairwise_disjoint(tmp_path,case):
    roots=_wp2g_fixture(tmp_path);b,t,o=roots
    target={'evidence':b,'verifier_trust':t,'parent':b.parent,'nested':b/'observer-root'}[case]
    if case=='nested':target.mkdir()
    r=_wp2g_run(roots,observer_trust_root=target)
    assert _wp2g_has(r,'policy_roots_not_disjoint');_wp2g_limits(r)


@pytest.mark.parametrize('role',['observer_policy','receipt_signature','receipt'])
def test_wp2g_carrier_change_during_read_rejected(tmp_path,monkeypatch,role):
    roots=_wp2g_fixture(tmp_path);m=_wp2g_module();execution=m.load_execution_checker();sig=execution.load_signature_checker()
    records=sig.load_record_checker();base=records.load_binding_checker();original=base.os.fstat
    inode=_wp2g_path(roots,role).stat().st_ino;calls=[]
    def changed(fd):
        s=original(fd)
        if s.st_ino==inode:
            calls.append(fd)
            if len(calls)==2:
                class Mutated:
                    def __getattr__(self,k):return getattr(s,k)+1 if k=='st_mtime_ns' else getattr(s,k)
                return Mutated()
        return s
    monkeypatch.setattr(base.os,'fstat',changed)
    monkeypatch.setattr(records,'load_binding_checker',lambda:base);monkeypatch.setattr(sig,'load_record_checker',lambda:records)
    monkeypatch.setattr(execution,'load_signature_checker',lambda:sig);monkeypatch.setattr(m,'load_execution_checker',lambda:execution)
    r=_wp2g_run(roots,module=m);assert any('carrier_changed_during_read' in i['code'] for i in r['issues']);_wp2g_limits(r)


@pytest.mark.parametrize('role',['observer_policy','trust_policy','receipt','receipt_signature'])
def test_wp2g_authentication_uses_retained_bytes_not_a_reopened_path(tmp_path,monkeypatch,role):
    roots=_wp2g_fixture(tmp_path);m=_wp2g_module();original=m.ReceiptReview.authenticate
    def swap(self,*args):
        _wp2g_path(roots,role).write_bytes(b'changed AFTER retained read\n')
        return original(self,*args)
    monkeypatch.setattr(m.ReceiptReview,'authenticate',swap)
    r=_wp2g_run(roots,module=m);assert r['status']=='LOCAL_RECEIPT_SIGNATURE_VERIFIED',r['issues']
    assert r['observed_digests'][role]==WP2G_PINS[role]
    assert _wp2c_hash(_wp2g_path(roots,role))!=r['observed_digests'][role];_wp2g_limits(r)


@pytest.mark.parametrize('failure',[RuntimeError('observer_backend_missing'),TimeoutError('observer_timeout')])
def test_wp2g_backend_failure_after_fresh_base_check_cannot_emit_success(monkeypatch,failure):
    m=_wp2g_module();execution=m.load_execution_checker();sig=execution.load_signature_checker();original=sig.OpenSSLVerifier;calls=[]
    def backend():
        calls.append(1)
        if len(calls)==2:raise failure
        return original()
    monkeypatch.setattr(sig,'OpenSSLVerifier',backend);monkeypatch.setattr(execution,'load_signature_checker',lambda:sig)
    monkeypatch.setattr(m,'load_execution_checker',lambda:execution)
    with pytest.raises(type(failure)):_wp2g_run(module=m)
    assert len(calls)==2


def test_wp2g_all_original_data_remains_unchanged_after_checks(tmp_path):
    roots=_wp2g_fixture(tmp_path);before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    a=_wp2g_run(roots);b=_wp2g_run(roots);assert a==b
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


@pytest.mark.parametrize('name',['observer_policy','execution_receipt_signature','execution_receipt_signature_report'])
def test_wp2g_schemas_self_contained(name):
    schema=load_json(ROOT/'schemas'/('anchor_integrity_'+name+'_v0_1.schema.json'))
    jsonschema.Draft202012Validator.check_schema(schema);_wp2_module()._assert_self_contained(schema)


@pytest.mark.parametrize('key',['release_authority_activation','accepted_as_execution_evidence','accepted_as_semantic_support',
 'accepted_as_independent_anchor','requested_checks_complete'])
def test_wp2g_report_schema_rejects_authority_promotion(key):
    r=_wp2g_run();r[key]=True
    schema=load_json(ROOT/'schemas/anchor_integrity_execution_receipt_signature_report_v0_1.schema.json')
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(r))


@pytest.mark.parametrize('field',['verifier_execution_attestation','observer_identity_authentication','observer_independence_verification',
 'request_precommitment_verification','challenge_freshness_verification','cycle_anchor_classification'])
def test_wp2g_report_cannot_promote_unperformed_measurements(field):
    r=_wp2g_run();r['unperformed_checks'][field]={'status':'completed','result':'verified','reason':None}
    schema=load_json(ROOT/'schemas/anchor_integrity_execution_receipt_signature_report_v0_1.schema.json')
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(r))


def test_wp2g_signer_label_cannot_cross_test_operator_domain():
    r=_wp2g_run();r['observer_statement_authentication']['result']='authorized_key_receipt_signature_verified'
    schema=load_json(ROOT/'schemas/anchor_integrity_execution_receipt_signature_report_v0_1.schema.json')
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(r))


def _wp2g_cli():
    cmd=[_wp2c_sys.executable,str(WP2G_TOOL),'--bundle-root',str(WP2G_DEMO/'bundle'),
         '--trust-root',str(WP2G_DEMO/'trust'),'--observer-trust-root',str(WP2G_DEMO/'observer-trust')]
    for k,v in WP2G_PATHS.items():cmd+=['--'+k.replace('_','-'),v,'--expected-'+k.replace('_','-')+'-sha256',WP2G_PINS[k]]
    cmd+=['--binding-profile','wp2b-json-pointer-v1','--signature-profile','pinned-ed25519-record-signers-v1',
          '--execution-profile','single-record-execution-contract-v1','--receipt-signature-profile',_wp2g_module().PROFILE,
          '--trust-domain','TEST','--verification-time-epoch',str(WP2E_EPOCH),'--record-id','synthetic-record-1',
          '--execution-id',WP2F_ID,'--challenge',WP2F_CHALLENGE,'--observer-id',WP2G_OBSERVER]
    return cmd


def test_wp2g_real_cli_receipt_signature_only():
    p=_wp2c_subprocess.run(_wp2g_cli(),capture_output=True,timeout=60)
    assert p.returncode==0,p.stderr;r=json.loads(p.stdout);assert r['status']=='LOCAL_RECEIPT_SIGNATURE_VERIFIED';_wp2g_limits(r)


@pytest.mark.parametrize('option',['--binding-profile','--signature-profile','--execution-profile','--receipt-signature-profile'])
def test_wp2g_cli_unknown_profiles_fail_without_success_json(option):
    cmd=_wp2g_cli();cmd[cmd.index(option)+1]='unknown';p=_wp2c_subprocess.run(cmd,capture_output=True,timeout=20)
    assert p.returncode==2 and not p.stdout


@pytest.mark.parametrize('argument',['paths','expected_digests'])
def test_wp2g_missing_or_additional_roles_cannot_be_inferred(argument):
    for kind in ('missing','extra'):
        v=dict(WP2G_PATHS if argument=='paths' else WP2G_PINS)
        if kind=='missing':v.pop('observer_policy')
        else:v['saved_report']='ignored'
        r=_wp2g_run(**{argument:v});assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INVALID';_wp2g_limits(r)


@pytest.mark.parametrize('value',[True,-1,253402300800,'1793836800'])
def test_wp2g_evaluation_epoch_is_explicit_typed_and_bounded(value):
    with pytest.raises(ValueError):_wp2g_run(verification_time_epoch=value)


def test_wp2g_no_live_execution_or_manifest_change():
    source=WP2G_TOOL.read_text()
    for bad in ('subprocess.run(', 'subprocess.Popen(', 'os.system(', 'eval(', 'exec(', 'import socket','import requests'):
        assert bad not in source
    for name in ('ci/tools-tests.list','ci/pytest-tests.list'):
        assert _manifest_entries(ROOT/name).count(TEST_PATH)==1
    assert 'OpenSSLVerifier()' in source and 'load_execution_checker()' in source


def test_wp2g_signing_input_has_exact_byte_and_domain_binding():
    m=_wp2g_module();a=m.signing_bytes('1'*64,'2'*64,'key',b'{}\n')
    assert a==b'PULSEMECH-ANCHOR-EXECUTION-RECEIPT-SIGNATURE-V1\0'+b'1'*64+b'\0'+b'2'*64+b'\0key\0{}\n'
    for args in [('x'*64,'2'*64,'key',b'{}'),('1'*64,'2'*64,'bad\0key',b'{}'),('1'*64,'2'*64,'key','{}'),
                 ('1'*64,'2'*64,'key',b' '*(m.MAX_RECEIPT_BYTES+1))]:
        with pytest.raises(ValueError):m.signing_bytes(*args)




@pytest.mark.parametrize('suffix',['\n','\r\n','\t',' '])
def test_wp2g_verifier_key_whitespace_alias_cannot_bypass_distinct_roles(tmp_path,suffix):
    roots=_wp2g_fixture(tmp_path);p=load_json(roots[2]/'policy.json');v=load_json(roots[1]/'policy.json')['keys'][0]
    p['keys'][0].update(public_key_hex=v['public_key_hex']+suffix,public_key_sha256=v['public_key_sha256'])
    _wp2c_write(roots[2],'policy.json',p)
    r=_wp2g_run(roots,_wp2g_resign(roots,seed=WP2E_SEED))
    assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INVALID';_wp2g_limits(r)


def test_wp2g_key_role_comparison_uses_bytes_even_for_upstream_accepted_spelling(tmp_path):
    roots=_wp2g_fixture(tmp_path);b,t,o=roots
    record_policy=load_json(t/'policy.json');v=record_policy['keys'][0]
    canonical=v['public_key_hex'];v['public_key_hex']=canonical+'\n';_wp2c_write(t,'policy.json',record_policy)
    _wp2e_resign((b,t))
    p=load_json(o/'policy.json');p['record_signer_policy_sha256']=_wp2c_hash(t/'policy.json')
    p['keys'][0].update(public_key_hex=canonical,public_key_sha256=v['public_key_sha256']);_wp2c_write(o,'policy.json',p)
    r=_wp2g_run(roots,_wp2g_resign(roots,seed=WP2E_SEED))
    assert _wp2g_has(r,'observer_key_reuses_verifier_key'),r['issues'];_wp2g_limits(r)


@pytest.mark.parametrize('role,field',[('observer_policy','key_id'),('receipt_signature','key_id'),
 ('receipt_signature','signature_hex'),('observer_policy','policy_id')])
def test_wp2g_new_ascii_identifier_and_encoding_fields_reject_trailing_newline(tmp_path,role,field):
    roots=_wp2g_fixture(tmp_path);p=_wp2g_path(roots,role);v=load_json(p)
    target=v['keys'][0] if role=='observer_policy' and field=='key_id' else v
    target[field]+='\n';p.write_text(json.dumps(v,indent=2)+'\n')
    r=_wp2g_run(roots,_wp2g_pins(roots));assert r['status']=='LOCAL_RECEIPT_SIGNATURE_INVALID';_wp2g_limits(r)


def test_wp2g_authorized_unattested_statement_does_not_become_observed_execution(tmp_path):
    roots=_wp2g_fixture(tmp_path);r=load_json(_wp2g_path(roots,'receipt'));r['observation_basis']='unattested_observer_statement'
    _wp2c_write(roots[0],WP2G_PATHS['receipt'],r)
    p=load_json(roots[2]/'policy.json');p['keys'][0]['observation_bases']=['unattested_observer_statement']
    _wp2c_write(roots[2],'policy.json',p)
    report=_wp2g_run(roots,_wp2g_resign(roots));assert report['status']=='LOCAL_RECEIPT_SIGNATURE_VERIFIED'
    assert report['observation_basis']=='unattested_observer_statement';_wp2g_limits(report)



# WP2H: fresh diagnostic integration; no authority or semantic promotion.
WP2H_TOOL = ROOT / 'tools/build_anchor_integrity_diagnostic_v0_1.py'
WP2H_DEMO = ROOT / 'examples/anchor_integrity_v0_1/wp2h_diagnostic_integration'


def _wp2h_module():
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location('anchor_wp2h_test', WP2H_TOOL)
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def _wp2h_fixture(tmp_path, receipt=False):
    import shutil
    config = tmp_path / 'selection'
    shutil.copytree(WP2H_DEMO / 'selection', config)
    if receipt:
        b, t, o = _wp2g_fixture(tmp_path / 'g')
        return config, b, t, o, 'receipt.json'
    b = tmp_path / 'bundle'
    shutil.copytree(WP2H_DEMO / 'cycle-bundle', b)
    return config, b, None, None, 'cycle.json'


def _wp2h_run(fixture=None, module=None, expected=None):
    if fixture is None:
        fixture = (WP2H_DEMO/'selection', WP2H_DEMO/'cycle-bundle', None, None, 'cycle.json')
    c, b, t, o, name = fixture
    m = module or _wp2h_module()
    return m.build_diagnostic(b, selection_root=c, selection_path=name,
        expected_selection_sha256=expected or _wp2c_hash(c/name), trust_root=t, observer_trust_root=o)


def _wp2h_repin(fixture, *, refresh=True):
    c, b, t, o, name = fixture
    selection = load_json(c/name)
    if refresh:
        _wp2d_refresh(b)
    for role, ref in selection['bindings'].items():
        root = t if role == 'trust_policy' else o if role == 'observer_policy' else b
        ref['sha256'] = _wp2c_hash(root/ref['path'])
    _wp2c_write(c, name, selection)
    return _wp2c_hash(c/name)


def _wp2h_limits(report):
    assert report['candidate_status'] == 'diagnostic_only'
    assert report['authority_effect'] == 'none'
    for key in ('release_authority_activation', 'requested_checks_complete',
                'accepted_as_execution_evidence', 'accepted_as_semantic_support',
                'accepted_as_independent_anchor', 'whole_response_completeness_established',
                'whole_response_cycle_freedom_established', 'legacy_v0_replaced', 'wp1_output_emitted'):
        assert report[key] is False
    assert report['loop_risk'] is None
    assert report['cycle_anchor_classification']['result'] is None
    for key in ('verified_binding_coverage', 'verified_support_coverage'):
        v = report['coverage'][key]
        assert v['value'] is v['numerator'] is v['denominator'] is None
        assert v['status'] in ('not_run', 'not_applicable')
    assert report['response_recommendation']['mode'] in ('BOUNDARY', 'ASK_FOR_ANCHOR')
    assert report['response_recommendation']['enforced'] is False
    for c in report['claim_diagnostics']:
        assert c['disposition'] == 'unresolved'
        assert c['accepted_as_semantic_support'] is False
    for v in report['unperformed_checks'].values():
        assert v['status'] == 'not_run' and v['result'] is None
    assert_valid('anchor_integrity_diagnostic_report_v0_1.schema.json', report)
    _wp2h_module().validate_arithmetic(report)


@pytest.mark.parametrize('role', ['selection', 'report'])
def test_wp2h_new_schemas_are_self_contained(role):
    schema = load_json(SCHEMA_DIR/f'anchor_integrity_diagnostic_{role}_v0_1.schema.json')
    jsonschema.Draft202012Validator.check_schema(schema)
    _wp2h_module().load_installed('check_anchor_integrity_bindings_v0_1.py')._assert_self_contained(schema)


@pytest.mark.parametrize('name', ['cycle.json', 'receipt.json'])
def test_wp2h_pinned_selection_examples_validate(name):
    assert_valid('anchor_integrity_diagnostic_selection_v0_1.schema.json', load_json(WP2H_DEMO/'selection'/name))


def test_wp2h_proxy_presence_and_support_are_separate():
    r = _wp2h_run()
    assert r['status'] == 'LOCAL_DIAGNOSTIC_BUILT'
    assert r['legacy_operational_proxy']['reported_value'] == 1.0
    assert r['coverage']['anchor_presence_coverage']['value'] == 0.5
    assert r['coverage']['anchor_presence_coverage']['numerator'] == 1
    assert r['coverage']['anchor_presence_coverage']['denominator'] == 2
    assert r['cycle_detection']['result'] == 'cycle_detected'
    assert r['response_recommendation']['mode'] == 'BOUNDARY'
    assert r['cyclic_components'][0]['witness']['nodes'][0] == r['cyclic_components'][0]['witness']['nodes'][-1]
    _wp2h_limits(r)


def test_wp2h_cycle_stage_matches_standalone_fresh_checker():
    r = _wp2h_run()
    b = WP2H_DEMO/'cycle-bundle'
    pins = tuple(_wp2c_hash(b/n) for n in ('input.json','carriers.json','record-set.json'))
    d = _wp2d_run(b,pins)
    m = _wp2h_module()
    assert r['stage_receipts']['dependency_cycles']['report_sha256'] == m.digest(m.report_bytes(d))
    assert r['cycle_detection'] == d['cycle_detection']
    assert r['cyclic_components'] == d['cyclic_components']


def test_wp2h_receipt_pipeline_preserves_narrow_authentication():
    f = (WP2H_DEMO/'selection',WP2G_DEMO/'bundle',WP2G_DEMO/'trust',WP2G_DEMO/'observer-trust','receipt.json')
    r = _wp2h_run(f)
    assert r['status'] == 'LOCAL_DIAGNOSTIC_BUILT'
    assert r['authenticated_receipt_statement'] is True
    assert r['receipt_scope']['covers_all_claims'] is False
    assert r['receipt_scope']['observation_basis'] == 'synthetic_fixture'
    assert r['receipt_scope']['verification_time_epoch'] == WP2E_EPOCH
    assert r['receipt_scope']['time_source'] == 'caller_supplied_not_authenticated'
    assert r['record_signature_authentication']['result'] == 'test_key_signatures_verified'
    assert r['receipt_statement_authentication']['result'] == 'test_key_receipt_signature_verified'
    assert r['cycle_detection']['result'] is None
    assert r['stage_receipts']['dependency_cycles']['executed'] is False
    standalone = _wp2g_run()
    m = _wp2h_module()
    assert r['stage_receipts']['receipt_signature']['report_sha256'] == m.digest(m.report_bytes(standalone))
    _wp2h_limits(r)


@pytest.mark.parametrize('proxy',[0,0.25,0.75,1])
def test_wp2h_numeric_proxy_does_not_drive_coverage_or_recommendation(tmp_path, proxy):
    f = _wp2h_fixture(tmp_path);c,b,_,_,_ = f
    before = _wp2h_run(f)
    legacy = load_json(b/'legacy.json');legacy['invariants']['anchor_coverage'] = proxy
    legacy['invariants']['loop_risk'] = 'high'
    legacy['state'] = 'ANCHOR_LOST';legacy['recommendation']['response_mode'] = 'SILENCE'
    _wp2c_write(b,'legacy.json',legacy)
    inp=load_json(b/'input.json');inp['legacy_overlay']['sha256']=_wp2c_hash(b/'legacy.json');_wp2c_write(b,'input.json',inp)
    _wp2h_repin(f)
    after = _wp2h_run(f)
    assert after['status']=='LOCAL_DIAGNOSTIC_BUILT'
    for key in ('coverage','claim_diagnostics','response_recommendation','cycle_detection','loop_risk'):
        assert after[key] == before[key]
    assert after['legacy_operational_proxy']['reported_value'] == proxy
    _wp2h_limits(after)


@pytest.mark.parametrize('proxy',[-1,1.1,True,'1',{},[]])
def test_wp2h_invalid_legacy_ratio_is_never_displayed_as_coverage(tmp_path,proxy):
    f=_wp2h_fixture(tmp_path);b=f[1];legacy=load_json(b/'legacy.json')
    legacy['invariants']['anchor_coverage']=proxy;_wp2c_write(b,'legacy.json',legacy)
    inp=load_json(b/'input.json');inp['legacy_overlay']['sha256']=_wp2c_hash(b/'legacy.json');_wp2c_write(b,'input.json',inp)
    _wp2h_repin(f);r=_wp2h_run(f)
    assert r['status']=='LOCAL_DIAGNOSTIC_INVALID'
    assert r['legacy_operational_proxy']['reported_value'] is None
    _wp2h_limits(r)


@pytest.mark.parametrize('case',['no_binding','no_invariants','null_ratio'])
def test_wp2h_missing_proxy_is_unknown_not_zero(tmp_path,case):
    f=_wp2h_fixture(tmp_path);b=f[1];inp=load_json(b/'input.json')
    if case=='no_binding':inp['legacy_overlay']=None
    else:
        legacy=load_json(b/'legacy.json')
        if case=='no_invariants':legacy.pop('invariants')
        else:legacy['invariants']['anchor_coverage']=None
        _wp2c_write(b,'legacy.json',legacy);inp['legacy_overlay']['sha256']=_wp2c_hash(b/'legacy.json')
    _wp2c_write(b,'input.json',inp);_wp2h_repin(f);r=_wp2h_run(f)
    assert r['status']==('LOCAL_DIAGNOSTIC_INVALID' if case=='no_binding' else 'LOCAL_DIAGNOSTIC_BUILT')
    assert r['legacy_operational_proxy']['status']=='unavailable'
    assert r['legacy_operational_proxy']['reported_value'] is None
    _wp2h_limits(r)


@pytest.mark.parametrize('state',['partial','invalid'])
def test_wp2h_partial_claim_set_has_no_denominator(tmp_path,state):
    f=_wp2h_fixture(tmp_path);b=f[1];cp=load_json(b/'claims.json')
    cp['claim_set']['materialization_status']=state;_wp2c_write(b,'claims.json',cp);_wp2h_repin(f)
    r=_wp2h_run(f);assert r['status']=='LOCAL_DIAGNOSTIC_INCOMPLETE'
    assert r['inventory']['declared_materialization_status']==state
    for v in r['coverage'].values():assert v['status']=='not_applicable' and v['value'] is None
    assert r['cycle_detection']['result'] is None
    _wp2h_limits(r)


def _wp2h_drop_relations(f):
    b=f[1];rp=load_json(b/'relations.json');rp['relations']=[];_wp2c_write(b,'relations.json',rp)
    rs=load_json(b/'record-set.json');rs['records']=[];_wp2c_write(b,'record-set.json',rs)
    graph=load_json(b/'graph.json');graph['dependency_edges']=[];_wp2c_write(b,'graph.json',graph)
    _wp2h_repin(f)


def test_wp2h_empty_anchor_inventory_requests_anchor_without_semantic_zero(tmp_path):
    f=_wp2h_fixture(tmp_path);_wp2h_drop_relations(f);r=_wp2h_run(f)
    assert r['status']=='LOCAL_DIAGNOSTIC_BUILT'
    assert r['coverage']['anchor_presence_coverage']['value']==0
    assert r['coverage']['verified_support_coverage']['value'] is None
    assert r['response_recommendation']['mode']=='ASK_FOR_ANCHOR'
    _wp2h_limits(r)


def test_wp2h_empty_claim_set_does_not_divide_by_zero(tmp_path):
    f=_wp2h_fixture(tmp_path);_wp2h_drop_relations(f);b=f[1]
    cp=load_json(b/'claims.json');cp['claim_set']['claims']=[];_wp2c_write(b,'claims.json',cp);_wp2h_repin(f)
    r=_wp2h_run(f)
    # WP1 requires a nonempty complete/partial claim set; preserve that rule.
    assert r['status']=='LOCAL_DIAGNOSTIC_INVALID'
    assert r['coverage']['anchor_presence_coverage']['status']=='not_run'
    assert r['coverage']['anchor_presence_coverage']['denominator'] is None
    assert r['response_recommendation']['mode']=='BOUNDARY'
    _wp2h_limits(r)


@pytest.mark.parametrize('result',['supported','contradicted','insufficient','unresolved'])
def test_wp2h_matching_verifier_declarations_do_not_become_claim_dispositions(tmp_path,result):
    f=_wp2h_fixture(tmp_path);b=f[1];rp=load_json(b/'relations.json')
    rp['relations'][0]['relation_verification']['result']=result
    _wp2c_write(b,'relations.json',rp);_wp2h_repin(f);r=_wp2h_run(f)
    assert r['status']=='LOCAL_DIAGNOSTIC_BUILT'
    assert r['claim_diagnostics'][0]['recorded_relations'][0]['declared_result']==result
    assert r['claim_diagnostics'][0]['disposition']=='unresolved'
    _wp2h_limits(r)


@pytest.mark.parametrize('relation_type',['references','supports','derived_from','contradicts','contextualizes'])
def test_wp2h_presence_counts_claims_once_regardless_of_relation_label(tmp_path,relation_type):
    f=_wp2h_fixture(tmp_path);b=f[1];rp=load_json(b/'relations.json')
    rel=deepcopy(rp['relations'][0]);rel['binding_id']='second-binding';rel['relation_type']=relation_type
    rel['relation_verification']={'status':'not_run','result':None,'reason':'synthetic_not_run'}
    rel['verifier_record_id']=None;rp['relations'].append(rel);_wp2c_write(b,'relations.json',rp);_wp2h_repin(f)
    r=_wp2h_run(f);assert r['status']=='LOCAL_DIAGNOSTIC_BUILT'
    assert r['coverage']['anchor_presence_coverage']['numerator']==1
    assert len(r['claim_diagnostics'][0]['recorded_relations'])==2
    _wp2h_limits(r)


def test_wp2h_absent_cycle_stage_is_not_low_risk(tmp_path):
    f=_wp2h_fixture(tmp_path);c,b,_,_,name=f;s=load_json(c/name);s['cycle_profile']='not_requested';_wp2c_write(c,name,s)
    r=_wp2h_run(f);assert r['status']=='LOCAL_DIAGNOSTIC_BUILT'
    assert r['cycle_detection']['status']=='not_run' and r['cycle_detection']['result'] is None
    assert r['input_requested_checks']['typed_evidence_cycle_check'] is True
    assert r['requested_checks_complete'] is False
    _wp2h_limits(r)


def test_wp2h_acyclic_projection_is_not_whole_response_proof(tmp_path):
    f=_wp2h_fixture(tmp_path);b=f[1];g=load_json(b/'graph.json');g['dependency_edges']=[]
    _wp2c_write(b,'graph.json',g);_wp2h_repin(f);r=_wp2h_run(f)
    assert r['status']=='LOCAL_DIAGNOSTIC_BUILT'
    assert r['cycle_detection']['result']=='no_cycle_detected_in_declared_graph'
    assert r['cyclic_components']==[]
    _wp2h_limits(r)


@pytest.mark.parametrize('case',['missing_file','no_binding','foreign_node','unknown_edge_type'])
def test_wp2h_graph_failures_never_become_empty_success(tmp_path,case):
    f=_wp2h_fixture(tmp_path);b=f[1]
    if case=='no_binding':
        inp=load_json(b/'input.json');inp['paradox_graph_binding']=None;_wp2c_write(b,'input.json',inp);_wp2h_repin(f)
    elif case in ('foreign_node','unknown_edge_type'):
        g=load_json(b/'graph.json')
        if case=='foreign_node':g['dependency_edges'][0]['to']['object_id']='foreign-claim'
        else:g['dependency_edges'][0]['type']='untyped_reference'
        _wp2c_write(b,'graph.json',g);_wp2h_repin(f)
    else:(b/'graph.json').unlink()
    r=_wp2h_run(f)
    assert r['status']==('LOCAL_DIAGNOSTIC_INCOMPLETE' if case in ('no_binding','missing_file') else 'LOCAL_DIAGNOSTIC_INVALID')
    assert r['cycle_detection']['result'] is None
    _wp2h_limits(r)


@pytest.mark.parametrize('path',['input.json','carriers.json','claims.json','evidence.json','relations.json','record-set.json','record-1.json','source.json','response.json','legacy.json'])
def test_wp2h_missing_material_propagates_incomplete(tmp_path,path):
    f=_wp2h_fixture(tmp_path);(f[1]/path).unlink();r=_wp2h_run(f)
    assert r['status']=='LOCAL_DIAGNOSTIC_INCOMPLETE'
    assert r['cycle_detection']['result'] is None
    _wp2h_limits(r)


@pytest.mark.parametrize('path',['input.json','carriers.json','claims.json','evidence.json','relations.json','record-set.json','record-1.json','source.json','response.json','graph.json'])
def test_wp2h_raw_material_substitution_fails_without_fallback(tmp_path,path):
    f=_wp2h_fixture(tmp_path);p=f[1]/path;p.write_bytes(p.read_bytes()+b' ');r=_wp2h_run(f)
    assert r['status']=='LOCAL_DIAGNOSTIC_INVALID'
    assert r['cycle_detection']['result'] is None
    _wp2h_limits(r)


@pytest.mark.parametrize('which',['request','receipt','receipt_signature','observer_policy','trust_policy'])
def test_wp2h_receipt_pipeline_missing_file_is_not_local_pipeline_fallback(tmp_path,which):
    f=_wp2h_fixture(tmp_path,True);c,b,t,o,name=f
    (_wp2g_path((b,t,o),which)).unlink();r=_wp2h_run(f)
    assert r['pipeline']=='receipt-signatures'
    assert r['status']=='LOCAL_DIAGNOSTIC_INCOMPLETE'
    assert r['authenticated_receipt_statement'] is False
    _wp2h_limits(r)


def test_wp2h_rehashed_receipt_tampering_invalidates_authentication(tmp_path):
    f=_wp2h_fixture(tmp_path,True);b,t,o=f[1:4]
    receipt=load_json(b/'execution/receipt.json');receipt['process']['duration_ms']+=1
    _wp2c_write(b,'execution/receipt.json',receipt);_wp2g_resign((b,t,o),sign=False);_wp2h_repin(f,refresh=False)
    r=_wp2h_run(f);assert r['status']=='LOCAL_DIAGNOSTIC_INVALID'
    assert r['authenticated_receipt_statement'] is False
    assert r['execution_contract_check']['status']=='completed'
    assert r['coverage']['anchor_presence_coverage']['value']==0.5
    _wp2h_limits(r)


def test_wp2h_receipt_and_cycle_stages_share_one_bound_input(tmp_path):
    f=_wp2h_fixture(tmp_path,True);c,b,t,o,name=f
    g=load_json(WP2D_DEMO/'graph.json')
    g['dependency_edges']=[_wp2d_edge('a',source='claim-1',target='claim-2'),_wp2d_edge('b',source='claim-2',target='claim-1')]
    _wp2c_write(b,'graph.json',g)
    inp=load_json(b/'input.json');inp['paradox_graph_binding']={'path':'graph.json','schema_version':'anchor_integrity_dependency_graph_v0_1','sha256':_wp2c_hash(b/'graph.json')}
    _wp2c_write(b,'input.json',inp);_wp2d_refresh(b);_wp2e_resign((b,t))
    rec=load_json(b/'execution/receipt.json');rec['record_binding']['sha256']=_wp2c_hash(b/'record-1.json');_wp2c_write(b,'execution/receipt.json',rec)
    _wp2g_resign((b,t,o));s=load_json(c/name);s['cycle_profile']='typed-dependencies-v1';_wp2c_write(c,name,s);_wp2h_repin(f,refresh=False)
    r=_wp2h_run(f);assert r['status']=='LOCAL_DIAGNOSTIC_BUILT',r['issues']
    assert r['authenticated_receipt_statement'] is True
    assert r['cycle_detection']['result']=='cycle_detected'
    assert all(v['executed'] for v in r['stage_receipts'].values())
    _wp2h_limits(r)


def test_wp2h_cycle_uses_retained_bytes_not_later_path_contents(tmp_path,monkeypatch):
    f=_wp2h_fixture(tmp_path);m=_wp2h_module();original=m.DiagnosticReview.cycles
    def mutate(self,cycle_module,records,record_review,reader,selection):
        assert 'graph.json' in reader.cache
        (f[1]/'graph.json').write_bytes(b'{}')
        return original(self,cycle_module,records,record_review,reader,selection)
    monkeypatch.setattr(m.DiagnosticReview,'cycles',mutate)
    r=_wp2h_run(f,module=m);assert r['status']=='LOCAL_DIAGNOSTIC_BUILT'
    assert r['cycle_detection']['result']=='cycle_detected'
    again=_wp2h_run(f);assert again['status']=='LOCAL_DIAGNOSTIC_INVALID'
    _wp2h_limits(r)


@pytest.mark.parametrize('mutation',['unknown_pipeline','unknown_binding','unknown_cycle','extra_field','saved_report','missing_pin','extra_pin','bad_hash','hash_newline','unsafe_path','wrong_context','case_collision'])
def test_wp2h_selection_rejects_unknown_or_unbound_inputs(tmp_path,mutation):
    f=_wp2h_fixture(tmp_path);c,b,t,o,name=f;s=load_json(c/name)
    if mutation=='unknown_pipeline':s['pipeline']='automatic'
    elif mutation=='unknown_binding':s['binding_profile']='latest'
    elif mutation=='unknown_cycle':s['cycle_profile']='low'
    elif mutation=='extra_field':s['command']='arbitrary executable'
    elif mutation=='saved_report':s['saved_success_report']={'status':'PASS'}
    elif mutation=='missing_pin':del s['bindings']['input']
    elif mutation=='extra_pin':s['bindings']['plugin']=deepcopy(s['bindings']['input'])
    elif mutation=='bad_hash':s['bindings']['input']['sha256']='f'*63
    elif mutation=='hash_newline':s['bindings']['input']['sha256']+='\n'
    elif mutation=='unsafe_path':s['bindings']['input']['path']='../input.json'
    elif mutation=='wrong_context':s['receipt_context']={}
    elif mutation=='case_collision':s['bindings']['carriers']['path']='INPUT.json'
    _wp2c_write(c,name,s);r=_wp2h_run(f)
    assert r['status']=='LOCAL_DIAGNOSTIC_INVALID'
    _wp2h_limits(r)


@pytest.mark.parametrize('raw',[b'{"profile":1,"profile":2}',b'{} trailing',b'[]',b'{"x":NaN}',b'\xff'])
def test_wp2h_strict_selection_json(tmp_path,raw):
    f=_wp2h_fixture(tmp_path);(f[0]/f[4]).write_bytes(raw);r=_wp2h_run(f)
    assert r['status']=='LOCAL_DIAGNOSTIC_INVALID';_wp2h_limits(r)


def test_wp2h_caller_selection_pin_is_not_derived_from_candidate(tmp_path):
    f=_wp2h_fixture(tmp_path);expected=_wp2c_hash(f[0]/f[4]);p=f[0]/f[4]
    p.write_bytes(p.read_bytes()+b' ');r=_wp2h_run(f,expected=expected)
    assert r['status']=='LOCAL_DIAGNOSTIC_INVALID'
    assert not any(v['executed'] for v in r['stage_receipts'].values())
    _wp2h_limits(r)


@pytest.mark.parametrize('kind',['symlink','hardlink','fifo'])
def test_wp2h_unsafe_selection_carriers_rejected(tmp_path,kind):
    import os
    f=_wp2h_fixture(tmp_path);p=f[0]/f[4];expected=_wp2c_hash(p);other=tmp_path/'other-selection';other.write_bytes(p.read_bytes());p.unlink()
    if kind=='symlink':p.symlink_to(other)
    elif kind=='hardlink':os.link(other,p)
    else:os.mkfifo(p)
    r=_wp2h_run(f,expected=expected);assert r['status']=='LOCAL_DIAGNOSTIC_INVALID';_wp2h_limits(r)


def test_wp2h_selection_root_cannot_contain_evidence_root(tmp_path):
    import shutil
    f=_wp2h_fixture(tmp_path);c,b,t,o,name=f;new=c/'nested';shutil.copytree(b,new)
    r=_wp2h_run((c,new,t,o,name));assert r['status']=='LOCAL_DIAGNOSTIC_INVALID';_wp2h_limits(r)


@pytest.mark.parametrize('which',['missing_verifier','missing_observer','same_roots','nested_root'])
def test_wp2h_receipt_roots_preserve_authorization_boundary(tmp_path,which):
    f=_wp2h_fixture(tmp_path,True);c,b,t,o,name=f
    if which=='missing_verifier':t=None
    elif which=='missing_observer':o=None
    elif which=='same_roots':o=t
    else:o=t/'nested';o.mkdir()
    r=_wp2h_run((c,b,t,o,name))
    assert r['status']==('LOCAL_DIAGNOSTIC_INCOMPLETE' if which.startswith('missing') else 'LOCAL_DIAGNOSTIC_INVALID')
    assert r['authenticated_receipt_statement'] is False;_wp2h_limits(r)


def test_wp2h_local_pipeline_rejects_unused_policy_roots(tmp_path):
    f=_wp2h_fixture(tmp_path);c,b,_,_,name=f;r=_wp2h_run((c,b,c,None,name))
    assert r['status']=='LOCAL_DIAGNOSTIC_INVALID';_wp2h_limits(r)


@pytest.mark.parametrize('key',['release_authority_activation','requested_checks_complete','accepted_as_execution_evidence',
 'accepted_as_semantic_support','accepted_as_independent_anchor','whole_response_completeness_established',
 'whole_response_cycle_freedom_established','legacy_v0_replaced','wp1_output_emitted'])
def test_wp2h_report_schema_rejects_authority_promotions(key):
    r=_wp2h_run();r[key]=True;assert_invalid('anchor_integrity_diagnostic_report_v0_1.schema.json',r)


@pytest.mark.parametrize('mutation',['low_risk','support_percentage','binding_percentage','supported_disposition','allow_supported','unmeasured_cycle','fake_receipt','proxy_coverage','enforced'])
def test_wp2h_report_cannot_relabel_missing_checks(mutation):
    r=_wp2h_run()
    if mutation=='low_risk':r['loop_risk']='low'
    elif mutation=='support_percentage':r['coverage']['verified_support_coverage']=dict(status='completed',numerator=2,denominator=2,value=1,reason=None)
    elif mutation=='binding_percentage':r['coverage']['verified_binding_coverage']=dict(status='completed',numerator=2,denominator=2,value=1,reason=None)
    elif mutation=='supported_disposition':r['claim_diagnostics'][0]['disposition']='supported'
    elif mutation=='allow_supported':r['response_recommendation']['mode']='ALLOW_SUPPORTED'
    elif mutation=='unmeasured_cycle':r['cycle_detection']['status']='not_run'
    elif mutation=='fake_receipt':r['authenticated_receipt_statement']=True
    elif mutation=='proxy_coverage':r['legacy_operational_proxy']['is_claim_evidence_coverage']=True
    else:r['response_recommendation']['enforced']=True
    assert_invalid('anchor_integrity_diagnostic_report_v0_1.schema.json',r)


@pytest.mark.parametrize('field,value',[('numerator',2),('denominator',3),('value',1.0)])
def test_wp2h_arithmetic_validator_rejects_plausible_wrong_ratios(field,value):
    m=_wp2h_module();r=_wp2h_run(module=m);r['coverage']['anchor_presence_coverage'][field]=value
    with pytest.raises(ValueError):m.validate_arithmetic(r)


def test_wp2h_markdown_is_separate_versioned_surface():
    m=_wp2h_module();r=_wp2h_run(module=m);text=m.render_markdown(r)
    assert 'WP2H diagnostic v0.1' in text and 'NOT claim coverage' in text
    assert '1 / 2 (0.500000)' in text and 'cycle_detected' in text
    assert '| Verified support coverage | not measured |' in text
    assert 'have NOT been replaced' in text
    assert '`ANSWER`' not in text and '`OPEN`' not in text


def test_wp2h_renderer_rejects_tampered_support_label():
    m=_wp2h_module();r=_wp2h_run(module=m);r['response_recommendation']['mode']='ALLOW_SUPPORTED'
    with pytest.raises(Exception):m.render_markdown(r)


def _wp2h_cli_args(fixture):
    import sys
    c,b,t,o,name=fixture
    args=[sys.executable,str(WP2H_TOOL),'--bundle-root',str(b),'--selection-root',str(c),
          '--selection',name,'--expected-selection-sha256',_wp2c_hash(c/name)]
    if t is not None:args+=['--trust-root',str(t)]
    if o is not None:args+=['--observer-trust-root',str(o)]
    return args


@pytest.mark.parametrize('fmt',['json','markdown'])
def test_wp2h_cli_uses_fresh_pipeline_for_both_formats(tmp_path,fmt):
    import subprocess
    f=_wp2h_fixture(tmp_path);p=subprocess.run(_wp2h_cli_args(f)+['--format',fmt],capture_output=True,timeout=60)
    assert p.returncode==0,p.stderr
    if fmt=='json':_wp2h_limits(json.loads(p.stdout))
    else:assert b'NOT claim coverage' in p.stdout and b'cycle_detected' in p.stdout


@pytest.mark.parametrize('mutation,exitcode',[('missing',2),('tamper',1)])
def test_wp2h_cli_propagates_failure_exit(tmp_path,mutation,exitcode):
    import subprocess
    f=_wp2h_fixture(tmp_path);p=f[1]/'source.json'
    if mutation=='missing':p.unlink()
    else:p.write_bytes(b'{}')
    run=subprocess.run(_wp2h_cli_args(f),capture_output=True,timeout=60)
    assert run.returncode==exitcode;_wp2h_limits(json.loads(run.stdout))


def test_wp2h_cli_has_no_output_overwrite_option(tmp_path):
    import subprocess
    f=_wp2h_fixture(tmp_path);target=tmp_path/'keep';target.write_bytes(b'untouched')
    run=subprocess.run(_wp2h_cli_args(f)+['--out',str(target)],capture_output=True,timeout=60)
    assert run.returncode==2 and run.stdout==b'' and target.read_bytes()==b'untouched'


def test_wp2h_deterministic_report_and_registered_module():
    m=_wp2h_module();assert m.report_bytes(_wp2h_run(module=m))==m.report_bytes(_wp2h_run(module=m))
    for name in ('tools-tests.list','pytest-tests.list'):
        assert _manifest_entries(ROOT/'ci'/name).count(TEST_PATH)==1


def test_wp2h_no_input_selected_module_or_saved_report_api():
    m=_wp2h_module()
    for name in ('../plugin.py','plugin.py','status.json'):
        with pytest.raises(ValueError):m.load_installed(name)





def test_wp2h_empty_invalid_claim_set_keeps_all_coverage_inapplicable(tmp_path):
    f=_wp2h_fixture(tmp_path);_wp2h_drop_relations(f);b=f[1]
    cp=load_json(b/'claims.json');cp['claim_set']['claims']=[];cp['claim_set']['materialization_status']='invalid'
    _wp2c_write(b,'claims.json',cp);_wp2h_repin(f);r=_wp2h_run(f)
    assert r['status']=='LOCAL_DIAGNOSTIC_INCOMPLETE'
    for v in r['coverage'].values():
        assert v['status']=='not_applicable' and v['denominator'] is None
    _wp2h_limits(r)


def test_wp2h_rehashed_outer_packets_cannot_hide_source_substitution(tmp_path):
    f=_wp2h_fixture(tmp_path);b=f[1];(b/'source.json').write_bytes(b'{"unexpected":"substitute"}\n')
    _wp2h_repin(f);r=_wp2h_run(f)
    assert r['status']=='LOCAL_DIAGNOSTIC_INVALID'
    assert r['coverage']['anchor_presence_coverage']['value'] is None
    _wp2h_limits(r)


def test_wp2h_base_check_runs_once_in_shared_receipt_chain(tmp_path,monkeypatch):
    f=_wp2h_fixture(tmp_path,True);m=_wp2h_module();real=m.load_installed
    receipt_module=real('check_anchor_integrity_receipt_signatures_v0_1.py')
    execution=receipt_module.load_execution_checker();signature=execution.load_signature_checker()
    records=signature.load_record_checker();base=records.load_binding_checker();calls=[]
    original=base.Review.review
    def counted(self,reader,*args,**kwargs):
        calls.append(id(reader));return original(self,reader,*args,**kwargs)
    monkeypatch.setattr(base.Review,'review',counted)
    monkeypatch.setattr(records,'load_binding_checker',lambda:base)
    monkeypatch.setattr(signature,'load_record_checker',lambda:records)
    monkeypatch.setattr(execution,'load_signature_checker',lambda:signature)
    monkeypatch.setattr(receipt_module,'load_execution_checker',lambda:execution)
    monkeypatch.setattr(m,'load_installed',lambda n:receipt_module if n=='check_anchor_integrity_receipt_signatures_v0_1.py' else real(n))
    r=_wp2h_run(f,module=m)
    assert r['status']=='LOCAL_DIAGNOSTIC_BUILT' and len(calls)==1
    _wp2h_limits(r)




# WP2I: correct the existing legacy Markdown reader, not raw v0 JSON semantics.
WP2I_EXAMPLE = EXAMPLE_DIR / 'wp2i_legacy_reader'
WP2I_SNAPSHOT = ROOT / 'tests/fixtures/anchor_integrity_v0_1/legacy_reader_7d5dc991.source.json'


def _wp2i_module():
    import importlib.util
    path = ROOT / 'scripts/render_anchor_integrity_overlay_v0_md.py'
    spec = importlib.util.spec_from_file_location('wp2i_legacy_reader_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _wp2i_example():
    return load_json(WP2I_EXAMPLE / 'legacy.json')


def _wp2i_render(payload=None, error=None):
    data = _wp2i_example() if payload is None else payload
    return _wp2i_module()._render_md(data, error, Path('legacy.json'))


def _wp2i_assert_boundary(text):
    assert 'Reader profile: `legacy-v0-proxy-boundary-v1`' in text
    assert 'not claim-evidence coverage' in text
    assert 'Fresh evidence checks executed: `false`' in text
    assert 'Authority effect: `none`' in text
    assert 'Release-authority activation: `false`' in text
    for label in ('Claim-level anchor presence', 'Verified binding coverage',
                  'Verified support coverage', 'Typed dependency-cycle detection',
                  'Loop risk', 'Contradiction risk', 'Independent-anchor classification'):
        assert f'| {label} | not_run | null |' in text
    for old in ('- State:', '- Recommendation:', '- anchor_coverage:',
                '- loop_risk:', '**ANCHORED**', '**ANSWER**', '**OPEN**',
                'Hallucination = Anchor Loss.'):
        assert old not in text
    assert 'This reader issues no response recommendation' in text


def _wp2i_cli(tmp_path, raw=None, extra=(), cwd=None):
    import subprocess
    import sys
    source = tmp_path / 'legacy.json'
    target = tmp_path / 'view.md'
    if raw is not None:
        source.write_bytes(raw)
    result = subprocess.run([sys.executable,
        str(ROOT / 'scripts/render_anchor_integrity_overlay_v0_md.py'),
        '--in', str(source), '--out', str(target), *map(str, extra)],
        capture_output=True, timeout=30, cwd=cwd)
    return result, source, target


def test_wp2i_snapshot_is_bound_to_pinned_exact_sources():
    snapshot = load_json(WP2I_SNAPSHOT)
    assert snapshot['source_repository'] == 'HKati/pulse-release-gates-0.1'
    assert snapshot['source_commit'] == '7d5dc991194a641661bd3e6d13c6db6f96e24ebd'
    assert snapshot['record_role'] == 'historical_source_bytes_for_reader_reproduction'
    assert snapshot['candidate_status'] == 'diagnostic_only'
    assert snapshot['authority_effect'] == 'none'
    expected = {
        'scripts/render_anchor_integrity_overlay_v0_md.py': (
            7966, '73ec5aeabeb05d6018be62fa79954e1c73dfe0a9',
            '6422e49219099c225f280cb8a7ce7b285d00e161f7c2c047b6d62cf44d905691'),
        'docs/ANCHOR_INTEGRITY_v0.md': (
            8134, '31188dfe1a33012d8869f035612d4d3e98515e0a',
            'f41ad8d562cfaf41b501be78f14050ddd6186c22f545e034fea3a3ce015f0b89'),
    }
    assert {r['path'] for r in snapshot['files']} == set(expected)
    for row in snapshot['files']:
        raw = base64.b64decode(row['content_base64'], validate=True)
        size, git_hash, sha = expected[row['path']]
        assert len(raw) == row['byte_length'] == size
        assert hashlib.sha256(raw).hexdigest() == row['content_sha256'] == sha
        assert hashlib.sha1(b'blob ' + str(size).encode() + b'\0' + raw).hexdigest() == row['git_blob_sha1'] == git_hash


def test_wp2i_historical_renderer_remains_reproducible(tmp_path):
    import subprocess
    import sys
    row = next(r for r in load_json(WP2I_SNAPSHOT)['files'] if r['path'].startswith('scripts/'))
    source = tmp_path / 'historical_renderer.py'
    source.write_bytes(base64.b64decode(row['content_base64'], validate=True))
    output = tmp_path / 'historical.md'
    before = (WP2I_EXAMPLE / 'legacy.json').read_bytes()
    result = subprocess.run([sys.executable, str(source), '--in', str(WP2I_EXAMPLE / 'legacy.json'),
                             '--out', str(output)], capture_output=True, timeout=30)
    assert result.returncode == 0
    text = output.read_text()
    assert '- anchor_coverage: `1.000`' in text
    assert '- loop_risk: `low`' in text
    assert '**ANCHORED**' in text and '**ANSWER**' in text and '**OPEN**' in text
    assert (WP2I_EXAMPLE / 'legacy.json').read_bytes() == before


def test_wp2i_doc_keeps_original_text_with_a_separate_boundary_notice():
    row = next(r for r in load_json(WP2I_SNAPSHOT)['files'] if r['path'].startswith('docs/'))
    original = base64.b64decode(row['content_base64'], validate=True).decode()
    current = (ROOT / row['path']).read_text()
    title, body = original.split('\n\n', 1)
    assert current.startswith(title + '\n\n> **Historical v0 design;')
    assert current.endswith(body)
    assert '[WP2I](ANCHOR_INTEGRITY_v0_1_WP2I_LEGACY_READER_BOUNDARY.md)' in current
    assert '[WP2H](ANCHOR_INTEGRITY_v0_1_WP2H_DIAGNOSTIC_INTEGRATION.md)' in current


def test_wp2i_raw_v0_producer_remains_exactly_preserved():
    raw = (ROOT / 'scripts/anchor_integrity_adapter_v0.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '3ceb60e9ca0a5d3a7d142bc91f5f51ca0376f54a37f33c3f359774f25c42f1d0'


def test_wp2i_expected_view_reproduces_example_without_evidence_promotion():
    m = _wp2i_module()
    rel = Path('examples/anchor_integrity_v0_1/wp2i_legacy_reader/legacy.json')
    actual = m._render_md(_wp2i_example(), None, rel)
    assert actual.encode() == (WP2I_EXAMPLE / 'expected.md').read_bytes()
    assert 'Reported gate-signal proxy: `1.0`' in actual
    _wp2i_assert_boundary(actual)


@pytest.mark.parametrize('value', [0, 1, 0.0, 1.0, 0.5, 0.00000000001, 0.9999999999999])
def test_wp2i_reports_only_the_unrounded_numeric_proxy(value):
    payload = _wp2i_example(); payload['invariants']['anchor_coverage'] = value
    text = _wp2i_render(payload)
    assert 'Reported value status: `reported`' in text
    assert f'Reported gate-signal proxy: `{json.dumps(value)}`' in text
    _wp2i_assert_boundary(text)


@pytest.mark.parametrize('value', [True, False, '1', '0.8', '100%', 100, -1, 1.0001,
    [], {}, float('nan'), float('inf'), -float('inf'), 10**100])
def test_wp2i_rejects_proxy_coercion_and_invalid_values(value):
    payload = _wp2i_example(); payload['invariants']['anchor_coverage'] = value
    text = _wp2i_render(payload)
    assert 'Reported value status: `invalid`' in text
    assert 'Reported gate-signal proxy: `null`' in text
    _wp2i_assert_boundary(text)


@pytest.mark.parametrize('missing', [True, False])
def test_wp2i_missing_proxy_is_unknown_not_zero(missing):
    payload = _wp2i_example()
    if missing: payload['invariants'].pop('anchor_coverage')
    else: payload['invariants']['anchor_coverage'] = None
    text = _wp2i_render(payload)
    assert 'Reported value status: `unavailable`' in text
    assert 'Reported gate-signal proxy: `null`' in text
    _wp2i_assert_boundary(text)


@pytest.mark.parametrize(('path', 'replacement'), [
    (('state',), 'ANCHORED'), (('state',), 'ANCHOR_LOST'), (('state',), 'UNKNOWN'),
    (('recommendation',), {'response_mode':'SILENCE','gate_action':'CLOSED'}),
    (('recommendation',), {'response_mode':'ALLOW_SUPPORTED','gate_action':'OPEN','rationale':'PROMOTE_SENTINEL'}),
    (('recommendation',), '<script>PROMOTE_SENTINEL</script>'),
    (('invariants','anchor_presence'), False), (('invariants','anchor_presence'), True),
    (('invariants','loop_risk'), 'high'), (('invariants','loop_risk'), 'medium'),
    (('invariants','loop_risk'), None), (('invariants','contradiction_risk'), 'high'),
    (('invariants','notes'), 'PROMOTE_SENTINEL'),
    (('evidence',), [{'kind':'verified','message':'PROMOTE_SENTINEL'}]),
    (('accepted_as_semantic_support',), True), (('authority_effect',), 'release'),
    (('checks',), {'cycle':{'status':'completed','result':'no_cycle_detected'}}),
])
def test_wp2i_legacy_advice_notes_and_added_claims_cannot_change_the_view(path, replacement):
    before = _wp2i_render(); payload = _wp2i_example(); parent = payload
    for key in path[:-1]: parent = parent[key]
    parent[path[-1]] = replacement
    actual = _wp2i_render(payload)
    assert actual == before and 'PROMOTE_SENTINEL' not in actual
    _wp2i_assert_boundary(actual)


@pytest.mark.parametrize('payload', [[], 'x', 7, True, {}, {'schema':'other','invariants':{}},
    {'schema':'anchor_integrity_diagnostic_report_v0_1','invariants':{}},
    {'schema':'anchor_integrity_v0'}, {'schema':'anchor_integrity_v0','invariants':[]},
    {'schema':'anchor_integrity_v0','invariants':None}])
def test_wp2i_wrong_format_never_masquerades_as_legacy_evidence(payload):
    text = _wp2i_module()._render_md(payload, None, Path('legacy.json'))
    assert '**UNAVAILABLE**' in text and 'LEGACY_PROXY_RENDERED' not in text
    _wp2i_assert_boundary(text)


@pytest.mark.parametrize('raw', [
    b'{', b'{} trailing', b'{}{}', b'\xff', b'\xef\xbb\xbf{}',
    b'{"schema":"anchor_integrity_v0","invariants":{"anchor_coverage":NaN}}',
    b'{"schema":"anchor_integrity_v0","invariants":{"anchor_coverage":Infinity}}',
    b'{"schema":"anchor_integrity_v0","invariants":{"anchor_coverage":-Infinity}}',
    b'{"schema":"anchor_integrity_v0","invariants":{"anchor_coverage":1e400}}',
    b'{"schema":"anchor_integrity_v0","invariants":{},"invariants":{}}',
    b'{"schema":"other","schema":"anchor_integrity_v0","invariants":{}}',
    b'{"schema":"anchor_integrity_v0","invariants":{},"meta":{"id":1,"id":2}}',
])
def test_wp2i_ambiguous_or_invalid_json_yields_unavailable(tmp_path, raw):
    p = tmp_path / 'bad.json'; p.write_bytes(raw)
    m = _wp2i_module(); data, error = m._read_json(p)
    assert data is None and error
    text = m._render_md(data, error, p)
    assert '**UNAVAILABLE**' in text
    _wp2i_assert_boundary(text)
    assert p.read_bytes() == raw


@pytest.mark.parametrize('kind', ['missing', 'directory', 'oversized', 'deep'])
def test_wp2i_unavailable_and_bounded_input_paths(tmp_path, monkeypatch, kind):
    m = _wp2i_module(); p = tmp_path / 'input'
    if kind == 'directory': p.mkdir()
    elif kind == 'oversized':
        monkeypatch.setattr(m, 'MAX_INPUT_BYTES', 16); p.write_bytes(b' ' * 17)
    elif kind == 'deep': p.write_bytes(b'[' * 3000 + b']' * 3000)
    data, error = m._read_json(p)
    assert data is None and error
    _wp2i_assert_boundary(m._render_md(data, error, p))


@pytest.mark.parametrize('value', [
    '`\n# INJECTED\n<script>alert(1)</script>', '```\n[run](javascript:alert(1))\n```',
    '<img src=x onerror=alert(1)>', '&lt;script&gt;', 'a\r\nb\t\x00', '\u202eabc',
    '\ud800', 'x' * 4000, {'x':'INJECTED'}, ['INJECTED'], float('inf'),
])
def test_wp2i_unverified_metadata_cannot_escape_its_literal_span(value):
    m = _wp2i_module(); literal = m._literal(value)
    assert literal.startswith('`') and literal.endswith('`') and literal.count('`') == 2
    assert '\n' not in literal and '\r' not in literal
    assert not any(c in literal for c in '<>&')
    payload = _wp2i_example();payload['meta']['generator'] = value
    text = m._render_md(payload, None, Path('input`\n# INJECTED'))
    assert '<script>' not in text and '\n# INJECTED' not in text
    _wp2i_assert_boundary(text)


@pytest.mark.parametrize('field', ['meta', 'inputs'])
def test_wp2i_malformed_optional_metadata_is_not_interpreted(field):
    payload = _wp2i_example();payload[field] = ['not-an-object']
    _wp2i_assert_boundary(_wp2i_render(payload))


def test_wp2i_render_is_deterministic_and_does_not_mutate_the_input():
    payload = _wp2i_example(); old = deepcopy(payload)
    assert _wp2i_render(payload) == _wp2i_render(payload)
    assert payload == old


def test_wp2i_cli_writes_corrected_view_without_changing_source(tmp_path):
    raw = (WP2I_EXAMPLE / 'legacy.json').read_bytes()
    result, source, target = _wp2i_cli(tmp_path, raw)
    assert result.returncode == 0 and result.stdout == b'' and result.stderr == b''
    assert source.read_bytes() == raw
    _wp2i_assert_boundary(target.read_text())


@pytest.mark.parametrize('raw', [None, b'not json', b'[]'])
def test_wp2i_ci_neutral_unavailable_placeholder_is_not_validation_success(tmp_path, raw):
    result, source, target = _wp2i_cli(tmp_path, raw)
    assert result.returncode == 0 and '**UNAVAILABLE**' in target.read_text()
    _wp2i_assert_boundary(target.read_text())


def test_wp2i_cli_default_paths_remain_compatible(tmp_path):
    import subprocess, sys
    m = _wp2i_module();p = tmp_path / m.DEFAULT_INPUT;p.parent.mkdir(parents=True)
    p.write_bytes((WP2I_EXAMPLE / 'legacy.json').read_bytes())
    result = subprocess.run([sys.executable,str(ROOT/'scripts/render_anchor_integrity_overlay_v0_md.py')],
                            cwd=tmp_path,capture_output=True,timeout=30)
    assert result.returncode == 0
    _wp2i_assert_boundary((tmp_path/m.DEFAULT_OUTPUT).read_text())


@pytest.mark.parametrize('alias', ['same', 'dot', 'symlink', 'hardlink', 'dangling_symlink', 'directory'])
def test_wp2i_cli_rejects_output_aliases_without_clobbering_inputs(tmp_path, alias):
    import os,subprocess,sys
    source=tmp_path/'legacy.json';raw=(WP2I_EXAMPLE/'legacy.json').read_bytes();source.write_bytes(raw)
    target=tmp_path/'view.md'
    if alias=='same':target=source
    elif alias=='dot':target=tmp_path/'sub'/'..'/'legacy.json';(tmp_path/'sub').mkdir()
    elif alias=='symlink':target.symlink_to(source)
    elif alias=='hardlink':os.link(source,target)
    elif alias=='dangling_symlink':target.symlink_to(tmp_path/'missing-target')
    else:target.mkdir()
    result=subprocess.run([sys.executable,str(ROOT/'scripts/render_anchor_integrity_overlay_v0_md.py'),
                            '--in',str(source),'--out',str(target)],capture_output=True,timeout=30)
    assert result.returncode==2 and result.stdout==b'' and source.read_bytes()==raw
    assert not (tmp_path/'missing-target').exists()


def test_wp2i_explicit_output_replacement_keeps_existing_cli_functionality(tmp_path):
    raw=(WP2I_EXAMPLE/'legacy.json').read_bytes();(tmp_path/'view.md').write_text('old display')
    result,source,target=_wp2i_cli(tmp_path,raw)
    assert result.returncode==0 and 'old display' not in target.read_text()
    assert source.read_bytes()==raw;_wp2i_assert_boundary(target.read_text())


def test_wp2i_runtime_has_no_network_crypto_or_evidence_execution_interface():
    import ast
    tree=ast.parse((ROOT/'scripts/render_anchor_integrity_overlay_v0_md.py').read_text())
    imports={n.names[0].name for n in ast.walk(tree) if isinstance(n,ast.Import)}
    assert imports <= {'argparse','json','math','sys'}
    assert 'subprocess' not in imports and 'requests' not in imports
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and
                   n.func.id in ('eval','exec','compile','__import__') for n in ast.walk(tree))
    for name in ('tools-tests.list','pytest-tests.list'):
        assert _manifest_entries(ROOT/'ci'/name).count(TEST_PATH)==1


def test_wp2i_document_keeps_raw_and_publication_boundaries_explicit():
    text=(ROOT/'docs/ANCHOR_INTEGRITY_v0_1_WP2I_LEGACY_READER_BOUNDARY.md').read_text()
    for marker in ('raw v0 JSON is unchanged','not a site deployment','not a fresh WP2H run',
                   'same `--in` / `--out`','legacy-v0-proxy-boundary-v1'):
        assert marker in text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
