#!/usr/bin/env python3
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "pulsemech_compute_post_run_producer_input_capture_manifest_v0.schema.json"
)
CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "pulsemech_compute_post_run_producer_input_capture_v0.json"
)
EXAMPLE_PATH = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_post_run_producer_input_capture_manifest_example_v0.json"
)
CAPTURE_TOOL_PATH = (
    ROOT / "tools" / "capture_pulsemech_compute_post_run_producer_input_v0.py"
)
OFFLINE_VALIDATOR_PATH = (
    ROOT
    / "tools"
    / "check_pulsemech_compute_post_run_producer_input_capture_v0.py"
)

EXPECTED_SCHEMA_IDENTITY = (
    71861,
    "65a29a18f1b9090f3dd338f9c4c1484b4d851df68ff19758670a4c53c58057bb",
    "f7256747704e87a4df312af6d20dad1c8bea6148",
)
EXPECTED_CONTRACT_IDENTITY = (
    38745,
    "ec3e31c9526f3bf931c633292bbff77efdf9cfbc61a0be634b6239c4acaccfbe",
    "66e03ebe4b7571888e0a8ac5322561353be2e892",
)
EXPECTED_EXAMPLE_IDENTITY = (
    16980,
    "8539975490b8e42321d2a32f9003cbc6030e12bfceaed3f7683215edcf57000a",
    "bdde78e902d4a670cf6ac857f737486d321a80d2",
)
EXPECTED_CAPTURE_TOOL_IDENTITY = (
    105104,
    "6f3dfa9e9b88240ef3da1c05f6a5278fd8b5d3796e683fff1cdc97ebf8a9e65d",
    "8d385606dfbea6eff691a8be29c17e82aa6ace37",
)
EXPECTED_OFFLINE_VALIDATOR_IDENTITY = (
    109943,
    "c37f1295949baa607fec839cac98a91f0c3d84b8223d7fe00d47589a3449fd05",
    "f25f1b46089d67f67a303226f0c7bc30449da9a1",
)
EXPECTED_EXAMPLE_BINDING_REVISION = (
    "9b0fdb2f2d30f4b0ad7abd20c19bf9a5a60d27ed"
)

EXPECTED_WORK_ORDER_BINDING = {
    "baseline_main": "abbb53a919919445138fcf4a3333e013e55c0470",
    "baseline_tree": "32e0353f2d5972edf5fb8225c44a4876f0b4a565",
    "issue": 2856,
    "planned_pr_count": 3,
    "pr_position": 1,
    "pr_role": "contract_and_capture_implementation",
    "repository": "HKati/pulse-release-gates-0.1",
    "step": "4A",
    "workstream": "compute_binding_and_transition_efficiency",
}

EXPECTED_POSITIVE_REQUIREMENTS = (
    "schema_is_valid_draft_2020_12",
    "contract_json_is_strict",
    "schema_binding_matches_exact_repository_object",
    "example_provenance_branch_validates",
    "observed_provenance_branch_validates",
    "example_and_observed_branch_mixing_rejected",
    "manifest_self_identity_absent",
    "exchange_metadata_self_identity_absent",
    "raw_response_bytes_preserved_exactly",
    "request_contract_exact",
    "selected_response_metadata_exact_or_explicitly_absent",
    "pagination_closed",
    "reported_total_equals_reconstructed_unique_jobs",
    "run_job_attempt_workflow_and_source_identities_consistent",
    "offline_validator_network_free",
    "offline_validator_separate_from_capture_tool",
    "fixture_capture_uses_no_network",
    "transactional_no_replace_publication",
    "secret_material_absent",
    "authority_effect_none",
    "same_preserved_capture_same_manifest_bytes",
    "same_preserved_capture_same_validation_result",
    "protected_repository_sources_unchanged",
)

EXPECTED_NEGATIVE_CASES = (
    "authorization_value_recorded",
    "best_effort_success",
    "capture_classified_as_authority_input",
    "capture_classified_as_runtime_observation",
    "capture_classified_as_runtime_packet",
    "capture_classified_as_transition_measurement",
    "capture_tool_verdict_trusted",
    "contract_binding_git_blob_mismatch",
    "contract_binding_path_mismatch",
    "contract_binding_role_mismatch",
    "contract_binding_sha256_mismatch",
    "contract_binding_size_mismatch",
    "contract_binding_source_revision_mismatch",
    "duplicate_job_id",
    "duplicate_jobs_page",
    "duplicate_step_number",
    "empty_response_body",
    "exchange_metadata_canonical_byte_mismatch",
    "exchange_metadata_self_reference",
    "existing_output_replacement",
    "final_next_link_present",
    "fork_subject",
    "hard_linked_member",
    "incomplete_pagination",
    "job_head_sha_mismatch",
    "job_run_attempt_mismatch",
    "job_run_id_mismatch",
    "job_workflow_name_mismatch",
    "latest_attempt_endpoint",
    "latest_run_endpoint",
    "manifest_canonicalization_failure",
    "manifest_schema_failure",
    "manifest_self_hash",
    "manifest_semantic_failure",
    "metadata_digest_mismatch",
    "metadata_size_mismatch",
    "missing_declared_member",
    "missing_jobs_page",
    "non_attempt_specific_jobs_endpoint",
    "non_contiguous_page_sequence",
    "non_get_request",
    "non_regular_member",
    "non_success_reference_run",
    "non_completed_run",
    "non_allowlisted_response_header",
    "partial_publication_success",
    "raw_header_inclusion",
    "raw_response_body_byte_mutation",
    "raw_response_body_normalization_claim",
    "raw_response_git_blob_mismatch",
    "raw_response_sha256_mismatch",
    "raw_response_size_mismatch",
    "redirect_admission",
    "reported_total_count_mismatch",
    "response_body_size_limit_exceeded",
    "schema_binding_git_blob_mismatch",
    "schema_binding_sha256_mismatch",
    "schema_binding_size_mismatch",
    "secret_value_in_diagnostics",
    "secret_value_in_output",
    "step_order_invalid",
    "symlinked_member",
    "total_capture_size_limit_exceeded",
    "truncated_response_body",
    "undeclared_extra_member",
    "unsafe_relative_path",
    "unsupported_content_encoding",
    "warning_only_success",
    "wrong_accept_encoding",
    "wrong_accept_header",
    "wrong_api_version",
    "wrong_content_type",
    "wrong_event",
    "wrong_host",
    "wrong_repository_full_name",
    "wrong_repository_id",
    "wrong_run_attempt",
    "wrong_run_id",
    "wrong_run_number",
    "wrong_source_commit",
    "wrong_user_agent",
    "wrong_workflow_id",
    "wrong_workflow_name",
    "wrong_workflow_path",
)

EXPECTED_FROZEN_SURFACES = (
    ".zenodo.json",
    "CITATION.cff",
    "Device_Ledger_contracts",
    "Device_Ledger_verifier",
    "Git_tags",
    "GitHub_Releases",
    "Reproduction_Capsule",
    "Zenodo_metadata",
    "Zenodo_record_relationships",
    "active_policy_sets",
    "check_gates.py",
    "compute_candidate_gate_identities",
    "existing_runtime_observation_packet_schema",
    "existing_runtime_observation_packet_validator",
    "iPhone_demonstrator",
    "planned_observed_relation_semantics",
    "release_decision_semantics",
    "release_required_gate_sets",
    "release_authority_path",
    "required_gate_sets",
    "status.json_semantics",
    "step_3G_artifact_observed_semantics",
)

EXPECTED_NOT_INFERRED_CATEGORIES = (
    "command_arguments_where_not_exposed",
    "downstream_state_consumption",
    "executed_command_bytes",
    "external_service_calls",
    "model_inferences",
    "network_byte_counts",
    "provider_usage",
    "resource_measurements",
    "shell_script_bytes",
    "transition_causality",
    "transition_necessity",
    "transition_sufficiency",
)

EXPECTED_SELECTED_HEADERS = (
    "Content-Encoding",
    "Content-Type",
    "Deprecation",
    "ETag",
    "Link",
    "Sunset",
    "X-GitHub-Request-Id",
)

EXPECTED_SUBJECT = {
    "event_name": "workflow_dispatch",
    "head_branch": "main",
    "head_repository": "HKati/pulse-release-gates-0.1",
    "head_repository_id": 1061766508,
    "repository": "HKati/pulse-release-gates-0.1",
    "repository_id": 1061766508,
    "repository_is_fork": False,
    "run_conclusion": "success",
    "run_created_utc": "2026-07-13T12:26:52Z",
    "run_started_utc": "2026-07-13T12:26:52Z",
    "run_status": "completed",
    "run_updated_utc": "2026-07-13T12:32:21Z",
    "same_repository_subject": True,
    "source_commit": "46b639706e23f80fe296a8893be18e2b5ab21f7e",
    "source_commit_is_exact_identity": True,
    "source_ref": "refs/heads/main",
    "source_ref_origin": (
        "declared_work_order_and_recorded_head_branch_reconstruction"
    ),
    "subject_class": "completed_historical_workflow_run_attempt",
    "subject_run_key": (
        "GITHUB_RUN_ID=29249887581|GITHUB_RUN_ATTEMPT=1|"
        "GITHUB_WORKFLOW=PULSE CI"
    ),
    "subject_run_key_origin": (
        "deterministic_reconstruction_from_run_id_attempt_and_workflow_name"
    ),
    "workflow_id": 191471316,
    "workflow_name": "PULSE CI",
    "workflow_path": ".github/workflows/pulse_ci.yml",
    "workflow_run_attempt": 1,
    "workflow_run_id": 29249887581,
    "workflow_run_number": 6066,
}

FORBIDDEN_MANIFEST_SELF_KEYS = {
    "manifest_git_blob_sha1",
    "manifest_sha256",
    "manifest_size_bytes",
}
FORBIDDEN_EXCHANGE_RECORD_SELF_KEYS = {
    "git_blob_sha1",
    "metadata_git_blob_sha1",
    "metadata_sha256",
    "metadata_size_bytes",
    "sha256",
    "size_bytes",
}


class StrictJSONError(ValueError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    framed = f"blob {len(payload)}\0".encode("ascii") + payload
    try:
        return hashlib.sha1(framed, usedforsecurity=False).hexdigest()
    except TypeError:
        return hashlib.sha1(framed).hexdigest()


def _parse_int(raw: str) -> int:
    if raw == "-0":
        raise StrictJSONError("negative_zero_forbidden")
    return int(raw, 10)


def _reject_float(raw: str) -> Any:
    raise StrictJSONError(f"floating_point_forbidden:{raw}")


def _reject_constant(raw: str) -> Any:
    raise StrictJSONError(f"non_finite_number_forbidden:{raw}")


def _object_pairs_no_duplicates(
    pairs: Sequence[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError(f"duplicate_decoded_key:{key}")
        result[key] = value
    return result


def strict_json_loads(payload: bytes, *, label: str) -> dict[str, Any]:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise StrictJSONError(f"{label}:utf8_bom_forbidden")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise StrictJSONError(f"{label}:malformed_utf8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_pairs_no_duplicates,
            parse_int=_parse_int,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, StrictJSONError) as exc:
        raise StrictJSONError(f"{label}:strict_json_invalid:{exc}") from exc
    if not isinstance(value, dict):
        raise StrictJSONError(f"{label}:top_level_must_be_object")
    return value


def _assert_no_floating_point(value: Any, *, path: str = "$") -> None:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise StrictJSONError(f"{path}:non_finite_number_forbidden")
        raise StrictJSONError(f"{path}:floating_point_forbidden")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_floating_point(item, path=f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            _assert_no_floating_point(item, path=f"{path}.{key}")


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    document = dict(value)
    _assert_no_floating_point(document)
    try:
        rendered = json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise StrictJSONError("canonical_json_serialization_failed") from exc
    return rendered + b"\n"


def _read_strict_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AssertionError(f"required file missing: {path.relative_to(ROOT)}")
    return strict_json_loads(path.read_bytes(), label=str(path.relative_to(ROOT)))


def _assert_exact_identity(
    path: Path,
    expected: tuple[int, str, str],
) -> bytes:
    if not path.is_file():
        raise AssertionError(f"required file missing: {path.relative_to(ROOT)}")
    payload = path.read_bytes()
    expected_size, expected_sha256, expected_blob = expected
    observed = (len(payload), sha256_bytes(payload), git_blob_sha1(payload))
    assert observed == expected, (
        f"exact identity mismatch for {path.relative_to(ROOT)}:\n"
        f"expected={expected!r}\n"
        f"observed={observed!r}\n"
        f"utf8_bom={payload.startswith(bytes.fromhex('efbbbf'))!r}\n"
        f"cr_count={payload.count(bytes([13]))}\n"
        f"lf_count={payload.count(bytes([10]))}\n"
        f"final_byte={payload[-1:].hex() if payload else None!r}\n"
        f"trailing_newline={payload.endswith(bytes([10]))!r}"
    )
    return payload


def _schema_errors(
    schema: Mapping[str, Any],
    value: Mapping[str, Any],
) -> list[jsonschema.ValidationError]:
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    return sorted(
        validator.iter_errors(value),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            error.validator or "",
            error.message,
        ),
    )


def _assert_schema_valid(
    schema: Mapping[str, Any],
    value: Mapping[str, Any],
) -> None:
    errors = _schema_errors(schema, value)
    assert not errors, "\n".join(
        f"/{'/'.join(str(part) for part in error.absolute_path)}: "
        f"{error.message}"
        for error in errors
    )


def _assert_schema_invalid(
    schema: Mapping[str, Any],
    value: Mapping[str, Any],
) -> None:
    errors = _schema_errors(schema, value)
    assert errors, "mutated manifest unexpectedly satisfied the schema"


def _iter_reference_keywords(
    value: Any,
    *,
    path: tuple[Any, ...] = (),
) -> Iterable[tuple[tuple[Any, ...], Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = path + (key,)
            if key in {"$ref", "$dynamicRef", "$recursiveRef"}:
                yield child_path, child
            yield from _iter_reference_keywords(child, path=child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_reference_keywords(child, path=path + (index,))


def _set_nested(value: dict[str, Any], path: Sequence[Any], replacement: Any) -> None:
    cursor: Any = value
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = replacement


def _observed_schema_witness(example: Mapping[str, Any]) -> dict[str, Any]:
    witness = copy.deepcopy(dict(example))
    witness["record_status"] = "observed"
    witness["manifest_identity"]["capture_scope"] = "historical_reference"
    witness["provenance"] = {
        "provenance_class": "observed_networked_capture",
        "capture_implementation": {
            "producer_id": (
                "pulsemech_compute_post_run_producer_input_capture_v0"
            ),
            "producer_name": (
                "PULSEmech compute post-run producer-input capture"
            ),
            "producer_version": "0.1.0",
            "producer_source": (
                "tools/capture_pulsemech_compute_post_run_producer_input_v0.py"
            ),
            "producer_source_revision": "a" * 40,
            "producer_source_sha256": "b" * 64,
            "execution_mode": "networked_capture",
            "dependency_policy": "python_standard_library_only",
        },
        "capture_workflow_execution": {
            "repository": "HKati/pulse-release-gates-0.1",
            "workflow_name": (
                "PULSEmech compute post-run producer-input capture"
            ),
            "workflow_id": 1,
            "workflow_path": (
                ".github/workflows/"
                "pulsemech_compute_post_run_producer_input_capture_v0.yml"
            ),
            "workflow_source_revision": "c" * 40,
            "workflow_source_sha256": "d" * 64,
            "workflow_run_id": 2,
            "workflow_run_attempt": 1,
            "workflow_run_key": (
                "GITHUB_RUN_ID=2|GITHUB_RUN_ATTEMPT=1|"
                "GITHUB_WORKFLOW=PULSEmech compute post-run "
                "producer-input capture"
            ),
            "event_name": "workflow_dispatch",
            "source_ref": "refs/heads/main",
            "permissions": {"actions": "read", "contents": "read"},
            "authority_effect": "none",
        },
    }
    witness["temporal_boundary"].update(
        {
            "capture_subject_class": "post_run_platform_response_snapshot",
            "capture_time_relation": "observed_at_capture_time",
            "capture_is_platform_response_snapshot": True,
            "reference_producer_input_eligible": True,
            "subject_run_completed_before_capture": True,
        }
    )
    witness["publication_boundary"]["publication_status"] = "completed"
    witness["authority_boundary"]["capture_subject_class"] = (
        "post_run_platform_response_snapshot"
    )
    return witness


def _module_import_roots(path: Path) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def _iter_keys(value: Any, *, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            current = f"{path}.{key}"
            yield current, key
            yield from _iter_keys(child, path=current)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_keys(child, path=f"{path}[{index}]")


def test_exact_repository_object_identities_and_strict_json() -> None:
    schema_payload = _assert_exact_identity(SCHEMA_PATH, EXPECTED_SCHEMA_IDENTITY)
    contract_payload = _assert_exact_identity(
        CONTRACT_PATH,
        EXPECTED_CONTRACT_IDENTITY,
    )
    example_payload = _assert_exact_identity(EXAMPLE_PATH, EXPECTED_EXAMPLE_IDENTITY)
    _assert_exact_identity(CAPTURE_TOOL_PATH, EXPECTED_CAPTURE_TOOL_IDENTITY)
    _assert_exact_identity(
        OFFLINE_VALIDATOR_PATH,
        EXPECTED_OFFLINE_VALIDATOR_IDENTITY,
    )

    strict_json_loads(schema_payload, label="schema")
    strict_json_loads(contract_payload, label="contract")
    example = strict_json_loads(example_payload, label="example")

    assert canonical_json_bytes(example) == example_payload
    assert not example_payload.startswith(b"\xef\xbb\xbf")
    assert example_payload.count(b"\r") == 0
    assert example_payload.count(b"\n") == 1
    assert example_payload.endswith(b"\n")


def test_schema_is_valid_draft_2020_12_and_reference_closed() -> None:
    schema = _read_strict_object(SCHEMA_PATH)
    jsonschema.Draft202012Validator.check_schema(schema)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == (
        "https://github.com/HKati/pulse-release-gates-0.1/"
        "schemas/"
        "pulsemech_compute_post_run_producer_input_capture_manifest_v0."
        "schema.json"
    )
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["errors"]["maxItems"] == 0
    assert schema["properties"]["ok"]["const"] is True

    references = list(_iter_reference_keywords(schema))
    assert references
    for path, reference in references:
        assert isinstance(reference, str), path
        assert reference.startswith("#"), (path, reference)


def test_normative_contract_identity_and_work_order_binding() -> None:
    contract = _read_strict_object(CONTRACT_PATH)

    assert contract["document_type"] == (
        "pulsemech_compute_post_run_producer_input_capture_contract"
    )
    assert contract["record_status"] == "normative_contract"
    assert contract["capture_contract_id"] == (
        "pulsemech_compute_post_run_producer_input_capture_v0"
    )
    assert contract["capture_contract_version"] == "0.1.0"
    assert contract["work_order_binding"] == EXPECTED_WORK_ORDER_BINDING
    assert tuple(contract["frozen_surfaces"]) == EXPECTED_FROZEN_SURFACES


def test_normative_contract_binds_exact_manifest_schema() -> None:
    contract = _read_strict_object(CONTRACT_PATH)
    schema = _read_strict_object(SCHEMA_PATH)
    binding = contract["schema_binding"]

    assert binding == {
        "byte_identity": "exact_repository_file_bytes",
        "document_type_const": (
            "pulsemech_compute_post_run_producer_input_capture_manifest"
        ),
        "git_blob_sha1": EXPECTED_SCHEMA_IDENTITY[2],
        "id": schema["$id"],
        "path": (
            "schemas/"
            "pulsemech_compute_post_run_producer_input_capture_manifest_v0."
            "schema.json"
        ),
        "schema_dialect": schema["$schema"],
        "schema_version_const": (
            "pulsemech_compute_post_run_producer_input_capture_manifest_v0"
        ),
        "sha256": EXPECTED_SCHEMA_IDENTITY[1],
        "size_bytes": EXPECTED_SCHEMA_IDENTITY[0],
    }
    assert schema["properties"]["schema_version"]["const"] == (
        binding["schema_version_const"]
    )
    assert schema["properties"]["document_type"]["const"] == (
        binding["document_type_const"]
    )


def test_contract_preserves_exact_response_byte_domain() -> None:
    contract = _read_strict_object(CONTRACT_PATH)
    canonical = contract["canonicalization_contract"]
    byte_domain = contract["response_byte_domain_contract"]
    content = contract["content_boundary"]

    assert canonical["canonicalization_profile"] == (
        "json-sort-keys-utf8-newline"
    )
    assert canonical["duplicate_object_keys"] == "forbidden"
    assert canonical["floating_point_numbers"] == "forbidden"
    assert canonical["negative_zero"] == "forbidden"
    assert canonical["non_finite_numbers"] == "forbidden"
    assert canonical["raw_response_body_canonicalization"] == "forbidden"
    assert canonical["raw_response_body_reserialization"] == "forbidden"
    assert canonical["unicode_normalization"] == "none"

    exact_domain = (
        "exact_http_entity_body_returned_to_capture_implementation_before_"
        "json_parsing_or_reserialization"
    )
    assert byte_domain["exact_byte_domain"] == exact_domain
    assert content["response_body_byte_domain"] == exact_domain
    for field in (
        "json_normalization",
        "json_reformatting",
        "key_reordering",
        "newline_rewriting",
        "whitespace_rewriting",
    ):
        assert byte_domain[field] == "forbidden"
    for field in (
        "http_chunk_framing_captured",
        "tls_frames_captured",
        "wire_level_packet_capture",
    ):
        assert byte_domain[field] is False


def test_contract_temporal_firewall_and_authority_boundary_are_closed() -> None:
    contract = _read_strict_object(CONTRACT_PATH)
    temporal = contract["temporal_boundary"]
    authority = contract["authority_boundary"]

    assert temporal == {
        "active_gate_eligible": False,
        "authority_effect": "none",
        "capture_is_compute_report": False,
        "capture_is_original_runtime_byte_stream": False,
        "capture_is_platform_response_snapshot": True,
        "capture_is_runtime_observation": False,
        "capture_is_runtime_observation_packet": False,
        "capture_is_transition_measurement": False,
        "capture_subject_class": "post_run_platform_response_snapshot",
        "capture_time_relation": "observed_at_capture_time",
        "future_active_path_requires_pre_decision_capture": True,
        "reference_producer_input_eligible": True,
        "retroactive_same_run_authority_admission_forbidden": True,
        "same_run_release_authority_eligible": False,
        "subject_run_completed_before_capture": True,
    }

    assert authority["write_mode"] == "post_run_producer_input_capture_only"
    assert authority["capture_subject_class"] == (
        "post_run_platform_response_snapshot"
    )
    assert authority["authority_effect"] == "none"
    for field, value in authority.items():
        if field in {"write_mode", "capture_subject_class", "authority_effect"}:
            continue
        assert value is False, (field, value)

    firewall = contract["temporal_firewall"]
    assert firewall["historical_reference_lane"] == [
        "completed_historical_run",
        "capture_time_platform_response_snapshot",
        "exact_preserved_producer_input",
        "offline_validation",
        "later_deterministic_reference_packet_production",
        "authority_effect_none",
    ]
    assert firewall["future_operational_lane"] == [
        "current_subject_run",
        "pre_decision_exact_source_capture",
        "runtime_observation_packet",
        "planned_observed_transition_relation",
        "transition_path_verification",
        "policy_bound_authority_decision",
    ]
    assert firewall["retroactive_same_run_authority_admission"] == "forbidden"


def test_contract_request_response_and_metadata_contracts_are_exact() -> None:
    contract = _read_strict_object(CONTRACT_PATH)
    request = contract["request_contract"]
    execution = contract["request_execution_contract"]
    admission = contract["response_admission_contract"]
    selected = contract["selected_response_metadata_contract"]

    assert request == {
        "accept": "application/vnd.github+json",
        "accept_encoding": "identity",
        "api_version": "2022-11-28",
        "authentication_environment_variable_name": "GH_TOKEN",
        "authentication_mode": "bearer_token_from_declared_environment_variable",
        "authorization_header_present": True,
        "authorization_value_recorded": False,
        "host": "api.github.com",
        "jobs_per_page": 100,
        "jobs_query_parameter_order": ["per_page", "page"],
        "latest_attempt_resolution_allowed": False,
        "latest_run_resolution_allowed": False,
        "method": "GET",
        "non_attempt_specific_jobs_endpoint_allowed": False,
        "redirect_policy": "forbidden",
        "redirects_followed": False,
        "scheme": "https",
        "token_value_written_to_diagnostics": False,
        "token_value_written_to_output": False,
        "user_agent": "pulsemech-compute-post-run-capture-v0/0.1.0",
    }
    assert execution["run_attempt_request"] == {
        "exact_request_target": (
            "/repos/HKati/pulse-release-gates-0.1/"
            "actions/runs/29249887581/attempts/1"
        ),
        "path_template": (
            "/repos/{owner}/{repository}/actions/runs/{run_id}/"
            "attempts/{run_attempt}"
        ),
        "query_parameters": [],
    }
    assert execution["jobs_page_request"] == {
        "exact_first_request_target": (
            "/repos/HKati/pulse-release-gates-0.1/"
            "actions/runs/29249887581/attempts/1/jobs?per_page=100&page=1"
        ),
        "path_template": (
            "/repos/{owner}/{repository}/actions/runs/{run_id}/"
            "attempts/{run_attempt}/jobs"
        ),
        "query_serialization": (
            "per_page=100&page={canonical_positive_decimal}"
        ),
    }
    assert admission["http_status"] == 200
    assert admission["redirect_observed"] is False
    assert admission["body_complete"] is True
    assert admission["body_truncated"] is False
    assert admission["non_200_response"] == "reject"
    assert admission["content_encoding"] == "absent_or_identity"
    assert admission["content_type"] == "application_json_with_optional_parameters"

    assert tuple(selected["allowlist"]) == EXPECTED_SELECTED_HEADERS
    assert selected["raw_request_headers_stored"] is False
    assert selected["raw_response_headers_stored"] is False
    assert selected["transport_only_metadata_is_subject_identity"] is False
    assert selected["duplicate_allowlisted_header_fields"] == "reject"
    assert selected["header_lookup"] == "case_insensitive"


def test_contract_subject_pagination_and_count_boundary_are_fixed() -> None:
    contract = _read_strict_object(CONTRACT_PATH)
    assert contract["initial_reference_subject"] == EXPECTED_SUBJECT
    assert contract["initial_reference_subject_expectations"] == {
        "expected_jobs_page_count": 1,
        "expected_jobs_total_count": 8,
        "later_link_header_controls_actual_page_count": True,
    }

    pagination = contract["pagination_contract"]
    assert pagination["pagination_mode"] == "attempt_specific_jobs_rel_next"
    assert pagination["per_page"] == 100
    assert pagination["first_page"] == 1
    assert pagination["maximum_page_count"] == 100
    assert pagination["page_sequence"] == (
        "strictly_ascending_contiguous_unique_beginning_at_1"
    )
    assert pagination["final_next_link_absence"] == "explicitly_recorded"
    assert pagination["jobs_page_total_count_relation"] == (
        "identical_on_every_page"
    )
    assert pagination["expected_initial_reference"] == {
        "first_page": 1,
        "page_count": 1,
        "per_page": 100,
        "reconstructed_unique_job_count": 8,
        "reported_total_count": 8,
    }


def test_contract_implementation_privacy_and_publication_separation() -> None:
    contract = _read_strict_object(CONTRACT_PATH)
    implementation = contract["implementation_boundary"]
    separation = contract["implementation_separation_contract"]
    privacy = contract["privacy_boundary"]
    publication = contract["publication_boundary"]
    failure = contract["failure_policy"]

    assert implementation == {
        "capture_tool_verdict_trusted": False,
        "compute_report_production_included": False,
        "future_runtime_observed_relation_included": False,
        "future_runtime_packet_production_included": False,
        "gate_materialization_included": False,
        "networked_capture_separate_from_offline_validation": True,
        "offline_validation_separate_from_future_packet_production": True,
        "offline_validator_imports_capture_implementation": False,
        "offline_validator_network_access": "none",
        "release_authority_included": False,
        "release_decision_included": False,
        "resource_measurement_included": False,
    }
    assert separation == {
        "capture_tool_dependency_policy": "python_standard_library_only",
        "capture_tool_role": (
            "networked_exact_response_acquisition_and_transactional_preservation"
        ),
        "capture_tool_verdict_trusted": False,
        "offline_validator_dependency_policy": (
            "python_standard_library_plus_jsonschema"
        ),
        "offline_validator_imports_capture_implementation": False,
        "offline_validator_network_access": "none",
        "offline_validator_role": (
            "separate_local_reconstruction_and_fail_closed_validation"
        ),
    }

    assert privacy["authorization_value_recorded"] is False
    assert privacy["raw_request_headers_included"] is False
    assert privacy["raw_response_headers_included"] is False
    assert privacy["selected_response_header_allowlist_only"] is True
    assert privacy["secret_material_included"] is False
    for field in (
        "token_value_in_diagnostics",
        "token_value_in_exchange_metadata",
        "token_value_in_manifest",
        "token_value_in_raw_responses",
    ):
        assert privacy[field] is False

    assert publication["transactional_publication"] is True
    assert publication["isolated_staging_directory"] is True
    assert publication["atomic_no_replace_publication"] is True
    assert publication["cleanup_on_failure_required"] is True
    for field in (
        "best_effort_success_allowed",
        "existing_output_overwrite_allowed",
        "partial_publication_accepted",
        "protected_source_overwrite_allowed",
        "repository_source_write_attempted",
        "warning_only_success_allowed",
    ):
        assert publication[field] is False

    assert failure == {
        "best_effort_success": "forbidden",
        "default": "fail_closed",
        "existing_output_replacement": "forbidden",
        "partial_publication_success": "forbidden",
        "permissive_fallback": "forbidden",
        "success_exit_status": 0,
        "terminal_rejection_exit_status": 2,
        "unresolved_or_mismatched_input": "reject",
        "warning_only_success": "forbidden",
    }


def test_contract_availability_and_claim_boundaries_are_honest() -> None:
    contract = _read_strict_object(CONTRACT_PATH)
    availability = contract["availability_boundary"]
    content = contract["content_boundary"]
    claims = contract["claim_boundary"]

    assert tuple(availability["not_inferred_categories"]) == (
        EXPECTED_NOT_INFERRED_CATEGORIES
    )
    assert availability["capture_source"] == "github_actions_rest_api"
    assert availability["platform_response_fields_only"] is True
    assert availability["log_interpretation_used"] is False
    assert availability["unstated_values_inferred"] is False
    assert availability["unknown_distinct_from_absent"] is True
    assert availability["unavailable_distinct_from_zero"] is True
    assert availability["platform_timestamp_is_resource_measurement"] is False
    assert availability["step_presence_is_transition_binding"] is False
    assert availability["post_run_platform_snapshot_is_runtime_observation"] is False

    assert content["capture_role"] == "producer_input_carrier"
    for field in (
        "contains_compute_report",
        "contains_executed_command_bytes",
        "contains_external_call_reconstruction",
        "contains_model_inference_reconstruction",
        "contains_resource_measurement",
        "contains_runner_process_telemetry",
        "contains_runtime_observation_packet",
        "contains_workflow_logs",
    ):
        assert content[field] is False

    assert claims["capture_role"] == "preserved_producer_input_source"
    assert claims["platform_response_snapshot_claim"] == "bounded_to_capture_time"
    for field, value in claims.items():
        if field in {"capture_role", "platform_response_snapshot_claim"}:
            continue
        assert value == "none", (field, value)


def test_contract_regression_surface_is_exact_and_complete() -> None:
    contract = _read_strict_object(CONTRACT_PATH)
    regression = contract["regression_contract"]

    assert tuple(regression["positive_requirements"]) == (
        EXPECTED_POSITIVE_REQUIREMENTS
    )
    assert tuple(regression["negative_cases"]) == EXPECTED_NEGATIVE_CASES
    assert len(regression["negative_cases"]) == len(
        set(regression["negative_cases"])
    )
    assert regression["ordinary_pr_ci_live_github_api_calls"] == "none"
    assert regression["tools_test_manifest_registration"] == (
        "every_new_regression_exactly_once"
    )
    assert regression["cardinality_guard_update"] == (
        "same_commit_as_tools_test_manifest_registration"
    )


def test_identity_graph_is_acyclic_and_excludes_self_hashes() -> None:
    contract = _read_strict_object(CONTRACT_PATH)
    graph = contract["identity_graph"]
    storage = contract["contract_storage"]

    assert graph["construction_order"] == [
        "manifest_schema",
        "normative_capture_contract",
        "networked_capture_implementation",
        "manual_capture_workflow",
        "exact_platform_response_bodies",
        "canonical_exchange_metadata_records",
        "capture_manifest",
        "external_repository_object_identities",
    ]
    assert set(graph["forbidden_bindings"]) == {
        "contract_self_hash",
        "contract_self_size",
        "exchange_metadata_record_to_its_own_file_hash",
        "exchange_metadata_record_to_its_own_file_size",
        "manifest_self_hash",
        "manifest_self_size",
        "manifest_self_git_blob_sha1",
        "manifest_to_containing_git_commit",
        "raw_response_body_reserialization",
    }
    assert storage["self_hash"] == "forbidden"
    assert storage["self_size"] == "forbidden"
    assert storage["self_canonicalization_claim"] is False


def test_canonical_example_validates_and_uses_example_provenance() -> None:
    schema = _read_strict_object(SCHEMA_PATH)
    example = _read_strict_object(EXAMPLE_PATH)
    _assert_schema_valid(schema, example)

    assert example["record_status"] == "example"
    assert example["manifest_identity"]["capture_scope"] == "example"
    assert example["provenance"] == {
        "capture_workflow_execution_claimed": False,
        "fixture_id": (
            "fixture:pulsemech-compute-post-run-producer-input-capture-"
            "example-v0"
        ),
        "fixture_source_path": (
            "examples/compute/"
            "pulsemech_compute_post_run_producer_input_capture_manifest_"
            "example_v0.json"
        ),
        "intended_capture_mode": "post_run_platform_response_snapshot",
        "intended_capture_tool_path": (
            "tools/capture_pulsemech_compute_post_run_producer_input_v0.py"
        ),
        "intended_capture_workflow_path": (
            ".github/workflows/"
            "pulsemech_compute_post_run_producer_input_capture_v0.yml"
        ),
        "networked_capture_execution_claimed": False,
        "provenance_class": "checked_in_contract_example",
        "schema_identity": (
            "pulsemech_compute_post_run_producer_input_capture_manifest_v0"
        ),
    }
    assert example["temporal_boundary"]["capture_subject_class"] == (
        "contract_example"
    )
    assert example["temporal_boundary"]["capture_time_relation"] == (
        "example_only"
    )
    assert example["temporal_boundary"]["capture_is_platform_response_snapshot"] is False
    assert example["temporal_boundary"]["reference_producer_input_eligible"] is False
    assert example["publication_boundary"]["publication_status"] == "example"
    assert example["authority_boundary"]["authority_effect"] == "none"


def test_observed_provenance_schema_witness_validates() -> None:
    schema = _read_strict_object(SCHEMA_PATH)
    example = _read_strict_object(EXAMPLE_PATH)
    witness = _observed_schema_witness(example)
    _assert_schema_valid(schema, witness)

    assert witness["record_status"] == "observed"
    assert witness["manifest_identity"]["capture_scope"] == (
        "historical_reference"
    )
    assert witness["provenance"]["provenance_class"] == (
        "observed_networked_capture"
    )
    assert witness["temporal_boundary"]["capture_is_platform_response_snapshot"] is True
    assert witness["temporal_boundary"]["reference_producer_input_eligible"] is True
    assert witness["publication_boundary"]["publication_status"] == "completed"


@pytest.mark.parametrize(
    ("mutation_path", "replacement"),
    (
        (("record_status",), "observed"),
        (("manifest_identity", "capture_scope"), "historical_reference"),
        (("temporal_boundary", "capture_subject_class"), (
            "post_run_platform_response_snapshot"
        )),
        (("temporal_boundary", "capture_time_relation"), "observed_at_capture_time"),
        (("temporal_boundary", "capture_is_platform_response_snapshot"), True),
        (("temporal_boundary", "reference_producer_input_eligible"), True),
        (("publication_boundary", "publication_status"), "completed"),
        (("authority_boundary", "capture_subject_class"), (
            "post_run_platform_response_snapshot"
        )),
    ),
)
def test_example_and_observed_branch_mixing_is_rejected(
    mutation_path: tuple[Any, ...],
    replacement: Any,
) -> None:
    schema = _read_strict_object(SCHEMA_PATH)
    example = _read_strict_object(EXAMPLE_PATH)
    mutated = copy.deepcopy(example)
    _set_nested(mutated, mutation_path, replacement)
    _assert_schema_invalid(schema, mutated)


def test_observed_and_example_branch_mixing_is_rejected() -> None:
    schema = _read_strict_object(SCHEMA_PATH)
    example = _read_strict_object(EXAMPLE_PATH)
    observed = _observed_schema_witness(example)

    mutations = (
        (("record_status",), "example"),
        (("manifest_identity", "capture_scope"), "example"),
        (("temporal_boundary", "capture_subject_class"), "contract_example"),
        (("temporal_boundary", "capture_time_relation"), "example_only"),
        (("temporal_boundary", "capture_is_platform_response_snapshot"), False),
        (("temporal_boundary", "reference_producer_input_eligible"), False),
        (("publication_boundary", "publication_status"), "example"),
        (("authority_boundary", "capture_subject_class"), "contract_example"),
    )
    for path, replacement in mutations:
        mutated = copy.deepcopy(observed)
        _set_nested(mutated, path, replacement)
        _assert_schema_invalid(schema, mutated)


@pytest.mark.parametrize(
    ("mutation_path", "replacement"),
    (
        (("request_contract", "method"), "POST"),
        (("request_contract", "host"), "example.invalid"),
        (("request_contract", "api_version"), "latest"),
        (("request_contract", "accept"), "application/json"),
        (("request_contract", "accept_encoding"), "gzip"),
        (("request_contract", "user_agent"), "unbound-client"),
        (("request_contract", "authorization_value_recorded"), True),
        (("temporal_boundary", "capture_is_runtime_observation"), True),
        (("temporal_boundary", "capture_is_runtime_observation_packet"), True),
        (("temporal_boundary", "capture_is_transition_measurement"), True),
        (("implementation_boundary", "capture_tool_verdict_trusted"), True),
        (("implementation_boundary", "offline_validator_network_access"), "full"),
        (("publication_boundary", "partial_publication_accepted"), True),
        (("publication_boundary", "warning_only_success_allowed"), True),
        (("publication_boundary", "best_effort_success_allowed"), True),
        (("privacy_boundary", "secret_material_included"), True),
        (("privacy_boundary", "token_value_in_manifest"), True),
        (("content_boundary", "raw_response_json_normalized"), True),
        (("content_boundary", "contains_runtime_observation_packet"), True),
        (("authority_boundary", "activates_compute_gate"), True),
        (("authority_boundary", "capture_is_release_decision"), True),
        (("authority_boundary", "capture_is_release_authority"), True),
        (("authority_boundary", "authority_effect"), "active"),
        (("ok",), False),
        (("errors",), ["warning"]),
    ),
)
def test_schema_rejects_closed_boundary_mutations(
    mutation_path: tuple[Any, ...],
    replacement: Any,
) -> None:
    schema = _read_strict_object(SCHEMA_PATH)
    example = _read_strict_object(EXAMPLE_PATH)
    mutated = copy.deepcopy(example)
    _set_nested(mutated, mutation_path, replacement)
    _assert_schema_invalid(schema, mutated)


def test_schema_rejects_unexpected_manifest_and_exchange_self_identity() -> None:
    schema = _read_strict_object(SCHEMA_PATH)
    example = _read_strict_object(EXAMPLE_PATH)

    top_level = copy.deepcopy(example)
    top_level["manifest_sha256"] = "0" * 64
    _assert_schema_invalid(schema, top_level)

    manifest_identity = copy.deepcopy(example)
    manifest_identity["manifest_identity"]["manifest_size_bytes"] = 1
    _assert_schema_invalid(schema, manifest_identity)

    exchange = copy.deepcopy(example)
    exchange["run_attempt_exchange"]["record"]["metadata_sha256"] = "0" * 64
    _assert_schema_invalid(schema, exchange)


def test_schema_rejects_non_attempt_specific_and_noncanonical_requests() -> None:
    schema = _read_strict_object(SCHEMA_PATH)
    example = _read_strict_object(EXAMPLE_PATH)

    mutations = (
        (
            ("run_attempt_exchange", "record", "request", "path"),
            "/repos/HKati/pulse-release-gates-0.1/actions/runs/29249887581",
        ),
        (
            ("run_attempt_exchange", "record", "request", "request_target"),
            "/repos/HKati/pulse-release-gates-0.1/actions/runs/29249887581/attempts/latest",
        ),
        (
            ("jobs_page_exchanges", 0, "record", "request", "path"),
            "/repos/HKati/pulse-release-gates-0.1/actions/runs/29249887581/jobs",
        ),
        (
            ("jobs_page_exchanges", 0, "record", "request", "request_target"),
            (
                "/repos/HKati/pulse-release-gates-0.1/"
                "actions/runs/29249887581/attempts/1/jobs?"
                "page=1&per_page=100"
            ),
        ),
    )
    for path, replacement in mutations:
        mutated = copy.deepcopy(example)
        _set_nested(mutated, path, replacement)
        _assert_schema_invalid(schema, mutated)


def test_example_contract_bindings_match_exact_repository_objects() -> None:
    example = _read_strict_object(EXAMPLE_PATH)
    bindings = example["contract_bindings"]

    assert bindings["manifest_schema"] == {
        "git_blob_sha1": EXPECTED_SCHEMA_IDENTITY[2],
        "path": (
            "schemas/"
            "pulsemech_compute_post_run_producer_input_capture_manifest_v0."
            "schema.json"
        ),
        "role": "manifest_schema",
        "sha256": EXPECTED_SCHEMA_IDENTITY[1],
        "size_bytes": EXPECTED_SCHEMA_IDENTITY[0],
        "source_revision": EXPECTED_EXAMPLE_BINDING_REVISION,
    }
    assert bindings["normative_contract"] == {
        "git_blob_sha1": EXPECTED_CONTRACT_IDENTITY[2],
        "path": (
            "contracts/pulsemech_compute_post_run_producer_input_capture_v0.json"
        ),
        "role": "normative_contract",
        "sha256": EXPECTED_CONTRACT_IDENTITY[1],
        "size_bytes": EXPECTED_CONTRACT_IDENTITY[0],
        "source_revision": EXPECTED_EXAMPLE_BINDING_REVISION,
    }


def test_example_exchange_metadata_projection_is_exact_and_acyclic() -> None:
    example = _read_strict_object(EXAMPLE_PATH)
    wrappers = [example["run_attempt_exchange"], *example["jobs_page_exchanges"]]

    for wrapper in wrappers:
        record = wrapper["record"]
        metadata = wrapper["metadata_member"]
        canonical = canonical_json_bytes(record)

        assert wrapper["metadata_record_canonical_bytes_equal_record"] is True
        assert metadata["canonical_reserialization_matches"] is True
        assert metadata["canonicalization"] == "json-sort-keys-utf8-newline"
        assert metadata["size_bytes"] == len(canonical)
        assert metadata["sha256"] == sha256_bytes(canonical)
        assert metadata["git_blob_sha1"] == git_blob_sha1(canonical)
        assert metadata["utf8_bom_present"] is False
        assert metadata["cr_count"] == 0
        assert metadata["lf_count"] == 1
        assert metadata["final_byte_hex"] == "0a"
        assert metadata["trailing_newline_present"] is True

        observed_record_keys = set(record)
        assert observed_record_keys.isdisjoint(FORBIDDEN_EXCHANGE_RECORD_SELF_KEYS)

    observed_manifest_keys = set(example["manifest_identity"])
    assert observed_manifest_keys.isdisjoint(FORBIDDEN_MANIFEST_SELF_KEYS)
    assert example["manifest_identity"]["manifest_self_hash_included"] is False
    assert example["manifest_identity"]["member_inventory_scope"] == (
        "all_capture_files_except_this_manifest"
    )


def test_example_member_inventory_counts_and_pagination_close() -> None:
    example = _read_strict_object(EXAMPLE_PATH)
    run_wrapper = example["run_attempt_exchange"]
    page_wrappers = example["jobs_page_exchanges"]

    raw_paths = [run_wrapper["record"]["response"]["body_member"]["path"]]
    raw_paths.extend(
        wrapper["record"]["response"]["body_member"]["path"]
        for wrapper in page_wrappers
    )
    metadata_paths = [run_wrapper["metadata_member"]["path"]]
    metadata_paths.extend(wrapper["metadata_member"]["path"] for wrapper in page_wrappers)
    all_paths = raw_paths + metadata_paths

    assert raw_paths == [
        "raw/run_attempt_response.json",
        "raw/jobs_page_0001_response.json",
    ]
    assert metadata_paths == [
        "metadata/run_attempt_exchange_v0.json",
        "metadata/jobs_page_0001_exchange_v0.json",
    ]
    assert len(all_paths) == len(set(all_paths)) == 4
    assert example["manifest_identity"]["manifest_file_name"] not in all_paths

    counts = example["counts"]
    assert counts["run_attempt_exchange_count"] == 1
    assert counts["jobs_page_exchange_count"] == len(page_wrappers) == 1
    assert counts["raw_response_member_count"] == len(raw_paths) == 2
    assert counts["exchange_metadata_member_count"] == len(metadata_paths) == 2
    assert counts["declared_non_manifest_member_count"] == len(all_paths) == 4
    assert counts["duplicate_job_id_count"] == 0
    assert counts["duplicate_step_number_count"] == 0
    assert counts["count_relations_verified"] is True

    pagination = example["pagination"]
    assert pagination == {
        "closure_status": "closed",
        "final_next_link_absent": True,
        "first_page": 1,
        "link_following_mode": "exact_rel_next",
        "link_header_absence_recorded": True,
        "maximum_page_count": 100,
        "page_count": 1,
        "page_sequence": [1],
        "pagination_mode": "attempt_specific_jobs_rel_next",
        "per_page": 100,
        "reconstructed_unique_job_count": 8,
        "reported_total_count": 8,
        "reported_total_equals_reconstructed": True,
    }
    relation = page_wrappers[0]["record"]["pagination_relation"]
    assert relation == {
        "is_final_page": True,
        "link_header_status": "absent",
        "next_page_number": None,
        "next_relation_status": "closed_by_absence",
        "next_request_target": None,
        "page_number": 1,
        "relation_source": "selected_link_header",
    }


def test_example_subject_run_and_jobs_summaries_are_consistent() -> None:
    example = _read_strict_object(EXAMPLE_PATH)
    subject = example["subject"]
    run_summary = example["run_attempt_exchange"]["record"]["response"]["summary"]
    page_summary = example["jobs_page_exchanges"][0]["record"]["response"]["summary"]

    assert subject == EXPECTED_SUBJECT
    assert run_summary == {
        "conclusion": subject["run_conclusion"],
        "created_at": subject["run_created_utc"],
        "event_name": subject["event_name"],
        "head_branch": subject["head_branch"],
        "head_repository": subject["head_repository"],
        "head_repository_id": subject["head_repository_id"],
        "head_sha": subject["source_commit"],
        "repository": subject["repository"],
        "repository_id": subject["repository_id"],
        "repository_is_fork": subject["repository_is_fork"],
        "run_started_at": subject["run_started_utc"],
        "same_repository_subject": subject["same_repository_subject"],
        "status": subject["run_status"],
        "updated_at": subject["run_updated_utc"],
        "workflow_id": subject["workflow_id"],
        "workflow_name": subject["workflow_name"],
        "workflow_path": subject["workflow_path"],
        "workflow_run_attempt": subject["workflow_run_attempt"],
        "workflow_run_id": subject["workflow_run_id"],
        "workflow_run_number": subject["workflow_run_number"],
    }

    assert page_summary["page_number"] == 1
    assert page_summary["per_page"] == 100
    assert page_summary["reported_total_count"] == 8
    assert page_summary["jobs_on_page"] == 8
    assert page_summary["step_records_on_page"] == 6
    assert len(page_summary["job_ids"]) == len(set(page_summary["job_ids"])) == 8
    for field in (
        "all_jobs_match_head_sha",
        "all_jobs_match_run_attempt",
        "all_jobs_match_subject_run",
        "all_jobs_match_workflow_name",
        "job_ids_unique_within_page",
        "status_conclusion_relations_valid",
        "step_numbers_unique_and_ordered_within_job",
    ):
        assert page_summary[field] is True

    counts = example["counts"]
    assert counts["reported_job_count"] == page_summary["reported_total_count"]
    assert counts["reconstructed_unique_job_count"] == len(page_summary["job_ids"])
    assert counts["reconstructed_step_record_count"] == (
        page_summary["step_records_on_page"]
    )


def test_example_request_targets_and_selected_headers_are_exact() -> None:
    example = _read_strict_object(EXAMPLE_PATH)
    run = example["run_attempt_exchange"]["record"]
    jobs = example["jobs_page_exchanges"][0]["record"]

    run_target = (
        "/repos/HKati/pulse-release-gates-0.1/"
        "actions/runs/29249887581/attempts/1"
    )
    jobs_target = run_target + "/jobs?per_page=100&page=1"

    assert run["request"]["method"] == "GET"
    assert run["request"]["path"] == run_target
    assert run["request"]["query_parameters"] == []
    assert run["request"]["request_target"] == run_target

    assert jobs["page_number"] == 1
    assert jobs["request"]["method"] == "GET"
    assert jobs["request"]["path"] == run_target + "/jobs"
    assert jobs["request"]["query_parameters"] == [
        {"name": "per_page", "value": "100"},
        {"name": "page", "value": "1"},
    ]
    assert jobs["request"]["request_target"] == jobs_target

    for record in (run, jobs):
        request = record["request"]
        assert request["scheme"] == "https"
        assert request["host"] == "api.github.com"
        assert request["accept"] == "application/vnd.github+json"
        assert request["api_version"] == "2022-11-28"
        assert request["accept_encoding"] == "identity"
        assert request["user_agent"] == (
            "pulsemech-compute-post-run-capture-v0/0.1.0"
        )
        assert request["authentication_environment_variable_name"] == "GH_TOKEN"
        assert request["authorization_header_present"] is True
        assert request["authorization_value_recorded"] is False
        assert request["redirects_allowed"] is False

        response = record["response"]
        assert response["http_status"] == 200
        assert response["redirect_observed"] is False
        assert response["body_complete"] is True
        assert response["body_truncated"] is False
        headers = response["selected_headers"]
        assert set(headers) == {
            "content_encoding",
            "content_type",
            "deprecation",
            "etag",
            "link",
            "sunset",
            "x_github_request_id",
        }
        assert headers["content_type"] == {
            "status": "present",
            "value": "application/json; charset=utf-8",
        }
        for name in (
            "content_encoding",
            "deprecation",
            "etag",
            "link",
            "sunset",
            "x_github_request_id",
        ):
            assert headers[name] == {"status": "absent", "value": None}


def test_source_import_boundaries_match_the_contract() -> None:
    capture_imports = _module_import_roots(CAPTURE_TOOL_PATH)
    validator_imports = _module_import_roots(OFFLINE_VALIDATOR_PATH)

    assert "http" in capture_imports
    assert "ssl" in capture_imports
    assert "jsonschema" not in capture_imports
    assert "referencing" not in capture_imports

    assert "jsonschema" in validator_imports
    assert "referencing" in validator_imports
    assert "http" not in validator_imports
    assert "socket" not in validator_imports
    assert "ssl" not in validator_imports
    assert "urllib" in validator_imports

    validator_source = OFFLINE_VALIDATOR_PATH.read_text(encoding="utf-8")
    assert "from urllib.parse import urlsplit" in validator_source
    assert "urllib.request" not in validator_source
    assert "_install_network_audit_guard" in validator_source
    assert "http.client.connect" in validator_source
    assert "socket.connect" in validator_source
    assert (
        'CAPTURE_TOOL_PATH = "tools/'
        'capture_pulsemech_compute_post_run_producer_input_v0.py"'
        in validator_source
    )


def test_contract_limits_are_exact_and_nonzero() -> None:
    contract = _read_strict_object(CONTRACT_PATH)
    assert contract["limits"] == {
        "maximum_exchange_metadata_size_bytes": 1048576,
        "maximum_jobs_page_count": 100,
        "maximum_jobs_per_page": 100,
        "maximum_response_body_size_bytes": 8388608,
        "maximum_step_records_per_job": 10000,
        "maximum_total_capture_size_bytes": 67108864,
        "redirect_limit": 0,
    }
    assert contract["transactional_publication_contract"] == {
        "atomic_no_replace_primitive": (
            "linux_renameat2_RENAME_NOREPLACE_or_fail_closed"
        ),
        "cleanup_exception_boundary": "BaseException",
        "cleanup_on_failure": "required",
        "existing_final_path": "reject",
        "file_creation": "exclusive_no_follow",
        "file_mode_during_capture": "0600",
        "final_publication": "single_atomic_directory_rename_without_replacement",
        "final_readback_validation": "required_before_exit_zero",
        "fsync_policy": [
            "every_output_file",
            "staging_directory",
            "publication_parent_directory",
        ],
        "isolated_staging_directory": True,
        "partial_output_success": "forbidden",
        "protected_repository_source_write": "forbidden",
        "safe_cleanup_rule": (
            "remove_only_owned_descriptor_bound_objects_else_retain"
        ),
        "staging_directory_mode": "0700",
        "staging_name_in_output_bytes": False,
    }


def test_strict_json_helper_rejects_ambiguous_numeric_and_key_forms() -> None:
    cases = (
        b'{"a":1,"a":2}\n',
        b'{"value":1.0}\n',
        b'{"value":NaN}\n',
        b'{"value":Infinity}\n',
        b'{"value":-0}\n',
        b"\xef\xbb\xbf{}\n",
    )
    for payload in cases:
        with pytest.raises(StrictJSONError):
            strict_json_loads(payload, label="fixture")
