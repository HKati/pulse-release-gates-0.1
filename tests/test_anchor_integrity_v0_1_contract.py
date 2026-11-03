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

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
