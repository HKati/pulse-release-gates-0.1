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

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
