#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "pulsemech_compute_subject_input_packet_v0.schema.json"
)
EXAMPLE_PATH = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_subject_input_packet_6066_example_v0.json"
)

EXPECTED_SCHEMA_SHA256 = (
    "81c274aaee7cd2aee015eda490cc82bd19f7556db35e2c3dc9995fbdb8d96e19"
)
EXPECTED_SCHEMA_SIZE_BYTES = 33513
EXPECTED_SCHEMA_LINE_COUNT = 1361

EXPECTED_EXAMPLE_SHA256 = (
    "bb0c50fe1bc68a9637a3dc246fcf43b216392958de28ca3c81c6f0aa5b1a2105"
)
EXPECTED_EXAMPLE_SIZE_BYTES = 46537
EXPECTED_EXAMPLE_LINE_COUNT = 736

EXAMPLE_REPOSITORY_PATH = (
    "examples/compute/"
    "pulsemech_compute_subject_input_packet_6066_example_v0.json"
)

CORE_SINGLETON_ROLE_BINDINGS = (
    "preservation_manifest",
    "preservation_readme",
    "preservation_checksums",
    "complete_package",
    "package_inventory",
    "package_completeness_report",
    "independent_verification_report",
    "run_metadata",
    "final_status",
    "status_baseline",
    "release_decision",
    "release_authority",
    "artifact_binding",
    "evidence_manifest",
    "recorded_verifier_report",
    "required_gate_evidence",
    "candidate_index",
)

LIST_ROLE_BINDINGS = (
    "candidate_records",
    "external_evidence_records",
    "attestation_records",
    "reader_surfaces",
)

LOCKED_FALSE_AUTHORITY_FIELDS = (
    "writes_subject_run",
    "writes_target_repository",
    "mutates_carrier",
    "changes_release_authority",
    "changes_gate_policy",
    "changes_gate_semantics",
    "creates_release_decision",
    "creates_gate_result",
    "activates_compute_gate",
    "creates_compute_budget",
    "packet_is_release_authority",
)


def load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


_SCHEMA = load_json(SCHEMA_PATH)
_EXAMPLE = load_json(EXAMPLE_PATH)

jsonschema.Draft202012Validator.check_schema(_SCHEMA)
_VALIDATOR = jsonschema.Draft202012Validator(
    _SCHEMA,
    format_checker=jsonschema.FormatChecker(),
)


def schema() -> dict[str, Any]:
    return _SCHEMA


def example() -> dict[str, Any]:
    return copy.deepcopy(_EXAMPLE)


def validator() -> jsonschema.Draft202012Validator:
    return _VALIDATOR


def validation_errors(instance: dict[str, Any]) -> list[str]:
    return [
        error.message
        for error in sorted(
            validator().iter_errors(instance),
            key=lambda item: (
                tuple(str(part) for part in item.path),
                item.message,
            ),
        )
    ]


def validate(instance: dict[str, Any]) -> None:
    validator().validate(instance)


def assert_invalid(instance: dict[str, Any]) -> None:
    assert validation_errors(instance)


def observed_packet() -> dict[str, Any]:
    packet = example()
    packet["record_status"] = "observed"
    packet.pop("fixture_provenance")
    packet["producer"] = {
        "ci_workflow_or_job_identity": (
            "PULSE CI / portable subject-input packet export"
        ),
        "producer_id": "pulsemech_compute_subject_input_packet_producer_v0",
        "producer_name": "PULSEmech compute subject-input packet producer",
        "producer_run_key": (
            "PACKET_EXPORT_RUN_ID=29249887581|"
            "PACKET_EXPORT_ATTEMPT=1"
        ),
        "producer_source": (
            "tools/build_pulsemech_compute_subject_input_packet_v0.py"
        ),
        "producer_source_revision": "a" * 40,
        "producer_source_sha256": "b" * 64,
        "producer_version": "0.1.0",
        "production_mode": "fixed_source_adapter",
    }
    packet["packet_identity"]["packet_scope"] = "fixed_source_adapter"
    return packet


def first_provider_bound_artifact(packet: dict[str, Any]) -> dict[str, Any]:
    return next(
        artifact
        for artifact in packet["artifacts"]
        if artifact["provider_binding"] is not None
    )


def render_canonical(value: dict[str, Any]) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def test_contract_files_exist_and_exact_file_identities_are_pinned() -> None:
    assert SCHEMA_PATH.is_file()
    assert EXAMPLE_PATH.is_file()

    schema_bytes = SCHEMA_PATH.read_bytes()
    example_bytes = EXAMPLE_PATH.read_bytes()

    assert len(schema_bytes) == EXPECTED_SCHEMA_SIZE_BYTES
    assert len(schema_bytes.splitlines()) == EXPECTED_SCHEMA_LINE_COUNT
    assert hashlib.sha256(schema_bytes).hexdigest() == EXPECTED_SCHEMA_SHA256

    assert len(example_bytes) == EXPECTED_EXAMPLE_SIZE_BYTES
    assert len(example_bytes.splitlines()) == EXPECTED_EXAMPLE_LINE_COUNT
    assert hashlib.sha256(example_bytes).hexdigest() == EXPECTED_EXAMPLE_SHA256


def test_schema_is_draft_2020_12_and_checked_in_example_validates() -> None:
    assert schema()["$schema"] == (
        "https://json-schema.org/draft/2020-12/schema"
    )
    jsonschema.Draft202012Validator.check_schema(schema())
    validate(example())


def test_checked_in_example_is_canonical_and_has_no_self_digest() -> None:
    packet = example()
    text = EXAMPLE_PATH.read_text(encoding="utf-8")

    assert text == render_canonical(packet)
    assert packet["record_status"] == "example"
    assert "producer" not in packet

    fixture = packet["fixture_provenance"]
    assert fixture == {
        "fixture_id": "fixture:pulse-ci-6066/subject-input/v0",
        "fixture_kind": "checked_in_contract_example",
        "fixture_source_path": EXAMPLE_REPOSITORY_PATH,
        "intended_production_mode": "fixed_source_adapter",
        "packet_producer_execution_claimed": False,
        "schema_identity": "pulsemech_compute_subject_input_packet_v0",
        "source_data_status": "historical_observed",
    }
    assert not any(
        "sha256" in key or "digest" in key
        for key in fixture
    )

    fixture["fixture_sha256"] = EXPECTED_EXAMPLE_SHA256
    assert_invalid(packet)


def test_exact_6066_historical_subject_and_carrier_identity_is_preserved() -> None:
    packet = example()
    subject = packet["subject"]
    carrier = packet["carrier"]

    assert subject["repository"] == "HKati/pulse-release-gates-0.1"
    assert subject["workflow_name"] == "PULSE CI"
    assert subject["workflow_run_id"] == 29249887581
    assert subject["workflow_run_number"] == 6066
    assert subject["workflow_run_attempt"] == 1
    assert subject["subject_run_key"] == (
        "GITHUB_RUN_ID=29249887581|"
        "GITHUB_RUN_ATTEMPT=1|"
        "GITHUB_WORKFLOW=PULSE CI"
    )
    assert subject["source_commit"] == (
        "46b639706e23f80fe296a8893be18e2b5ab21f7e"
    )
    assert subject["release_candidate_id"] == "main"
    assert subject["decision"] == "ALLOW"

    assert packet["record_status"] == "example"
    assert packet["fixture_provenance"]["source_data_status"] == (
        "historical_observed"
    )
    assert carrier["carrier_kind"] == "preservation_archive"
    assert carrier["sha256"] == (
        "7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966"
    )
    assert carrier["size_bytes"] == 44660


def test_top_level_identity_fields_and_additional_properties_are_locked() -> None:
    mutations = {
        "schema_version": "wrong",
        "packet_type": "wrong",
        "record_status": "unknown",
    }
    for field, value in mutations.items():
        packet = example()
        packet[field] = value
        assert_invalid(packet)

    packet = example()
    packet["unexpected"] = True
    assert_invalid(packet)


def test_example_fixture_branch_requires_fixture_and_forbids_producer() -> None:
    packet = example()
    del packet["fixture_provenance"]
    assert_invalid(packet)

    packet = example()
    packet["producer"] = observed_packet()["producer"]
    assert_invalid(packet)

    packet = example()
    packet["record_status"] = "observed"
    assert_invalid(packet)


def test_observed_branch_requires_producer_and_forbids_fixture() -> None:
    packet = observed_packet()
    validate(packet)

    without_producer = observed_packet()
    del without_producer["producer"]
    assert_invalid(without_producer)

    with_fixture = observed_packet()
    with_fixture["fixture_provenance"] = example()["fixture_provenance"]
    assert_invalid(with_fixture)


def test_example_packet_scope_is_example_only() -> None:
    for scope in (
        "current_run",
        "post_run_preservation",
        "fixed_source_adapter",
    ):
        packet = example()
        packet["packet_identity"]["packet_scope"] = scope
        assert_invalid(packet)


def test_observed_packet_scopes_are_non_example() -> None:
    for scope in (
        "current_run",
        "post_run_preservation",
        "fixed_source_adapter",
    ):
        packet = observed_packet()
        packet["packet_identity"]["packet_scope"] = scope
        validate(packet)

    packet = observed_packet()
    packet["packet_identity"]["packet_scope"] = "example"
    assert_invalid(packet)


def test_example_carrier_class_is_independent_from_packet_status() -> None:
    for carrier_kind in (
        "preservation_archive",
        "current_run_export_archive",
        "provider_artifact_archive",
        "example_archive",
    ):
        packet = example()
        packet["carrier"]["carrier_kind"] = carrier_kind
        validate(packet)


def test_observed_carrier_forbids_example_archive() -> None:
    for carrier_kind in (
        "preservation_archive",
        "current_run_export_archive",
        "provider_artifact_archive",
    ):
        packet = observed_packet()
        packet["carrier"]["carrier_kind"] = carrier_kind
        validate(packet)

    packet = observed_packet()
    packet["carrier"]["carrier_kind"] = "example_archive"
    assert_invalid(packet)


def test_fixture_provenance_literals_and_classifications_are_locked() -> None:
    packet = example()
    fixture = packet["fixture_provenance"]

    fixture["fixture_kind"] = "generated_example"
    assert_invalid(packet)

    packet = example()
    packet["fixture_provenance"]["schema_identity"] = "wrong"
    assert_invalid(packet)

    packet = example()
    packet["fixture_provenance"]["packet_producer_execution_claimed"] = True
    assert_invalid(packet)

    for source_data_status in ("historical_observed", "synthetic"):
        packet = example()
        packet["fixture_provenance"]["source_data_status"] = (
            source_data_status
        )
        validate(packet)

    packet = example()
    packet["fixture_provenance"]["source_data_status"] = "observed"
    assert_invalid(packet)

    for mode in (
        "current_run_export",
        "post_run_export",
        "fixed_source_adapter",
    ):
        packet = example()
        packet["fixture_provenance"]["intended_production_mode"] = mode
        validate(packet)

    packet = example()
    packet["fixture_provenance"]["intended_production_mode"] = "example"
    assert_invalid(packet)


def test_producer_identity_is_exact_complete_and_non_example() -> None:
    required_fields = tuple(schema()["$defs"]["producer"]["required"])

    for field in required_fields:
        packet = observed_packet()
        del packet["producer"][field]
        assert_invalid(packet)

    invalid_mutations = {
        "producer_id": "",
        "producer_name": "",
        "producer_version": "v0",
        "producer_source": "",
        "producer_source_revision": "a" * 39,
        "producer_source_sha256": "b" * 63,
        "ci_workflow_or_job_identity": "",
        "producer_run_key": "",
        "production_mode": "example",
    }
    for field, value in invalid_mutations.items():
        packet = observed_packet()
        packet["producer"][field] = value
        assert_invalid(packet)

    packet = observed_packet()
    packet["producer"]["unexpected"] = True
    assert_invalid(packet)


def test_packet_identity_is_namespaced_canonical_and_utc_bound() -> None:
    packet = example()
    packet["packet_identity"]["packet_id"] = "packet-without-prefix"
    assert_invalid(packet)

    packet = example()
    packet["packet_identity"]["carrier_id"] = "carrier-without-prefix"
    assert_invalid(packet)

    packet = example()
    packet["packet_identity"]["canonicalization"] = "unspecified"
    assert_invalid(packet)

    packet = example()
    packet["packet_identity"]["packet_created_utc"] = (
        "2026-07-22T17:17:19+00:00"
    )
    assert_invalid(packet)


def test_subject_identity_fields_are_required_and_typed() -> None:
    required_fields = tuple(schema()["$defs"]["subject"]["required"])

    for field in required_fields:
        packet = example()
        del packet["subject"][field]
        assert_invalid(packet)

    for field in (
        "workflow_run_id",
        "workflow_run_number",
        "workflow_run_attempt",
    ):
        packet = example()
        packet["subject"][field] = 0
        assert_invalid(packet)

    packet = example()
    packet["subject"]["source_commit"] = "a" * 39
    assert_invalid(packet)

    for field in (
        "policy_sha256",
        "final_status_sha256",
        "release_decision_sha256",
    ):
        packet = example()
        packet["subject"][field] = "a" * 63
        assert_invalid(packet)

    packet = example()
    packet["subject"]["decision"] = "PROD-PASS"
    assert_invalid(packet)

    packet = example()
    packet["subject"]["active_policy_sets"] = []
    assert_invalid(packet)

    packet = example()
    packet["subject"]["active_policy_sets"] = ["required", "required"]
    assert_invalid(packet)

    packet = example()
    packet["subject"]["materialized_gate_set_sha256"] = None
    validate(packet)


def test_authority_sources_are_role_revision_digest_and_size_bound() -> None:
    expected_roles = {
        "workflow": "workflow",
        "policy": "policy",
        "gate_registry": "gate_registry",
    }

    for source_name, role in expected_roles.items():
        packet = example()
        source = packet["authority_sources"][source_name]
        assert source["role"] == role
        assert len(source["source_revision"]) == 40
        assert len(source["sha256"]) == 64
        assert source["size_bytes"] >= 0

        source["role"] = "other"
        assert_invalid(packet)

        packet = example()
        packet["authority_sources"][source_name]["source_revision"] = (
            "a" * 39
        )
        assert_invalid(packet)

        packet = example()
        packet["authority_sources"][source_name]["sha256"] = "b" * 63
        assert_invalid(packet)

        packet = example()
        packet["authority_sources"][source_name]["size_bytes"] = -1
        assert_invalid(packet)

    packet = example()
    additional = packet["authority_sources"]["additional_sources"][0]
    additional["source_revision"] = None
    validate(packet)

    packet = example()
    packet["authority_sources"]["additional_sources"][0]["role"] = "workflow"
    assert_invalid(packet)


def test_carrier_binding_is_immutable_zip_digest_bound_and_external() -> None:
    invalid_mutations = {
        "carrier_id": "not-a-carrier-id",
        "carrier_kind": "directory",
        "path_or_uri": "",
        "media_type": "application/octet-stream",
        "sha256": "a" * 63,
        "size_bytes": 0,
        "immutable": False,
        "artifact_payload_mode": "embedded",
    }

    for field, value in invalid_mutations.items():
        packet = example()
        packet["carrier"][field] = value
        assert_invalid(packet)

    packet = example()
    packet["carrier"]["provider_binding"] = None
    validate(packet)


def test_provider_binding_contract_is_exact_when_present() -> None:
    packet = example()
    artifact = first_provider_bound_artifact(packet)
    provider = artifact["provider_binding"]
    assert isinstance(provider, dict)

    required_fields = tuple(schema()["$defs"]["provider_binding"]["required"])
    for field in required_fields:
        mutated = example()
        provider_mutated = first_provider_bound_artifact(mutated)[
            "provider_binding"
        ]
        assert isinstance(provider_mutated, dict)
        del provider_mutated[field]
        assert_invalid(mutated)

    invalid_mutations = {
        "provider": "unknown-provider",
        "provider_artifact_id": "",
        "provider_artifact_name": "",
        "provider_sha256": "a" * 63,
        "provider_size_bytes": -1,
        "created_utc": "2026-07-13T12:30:11+00:00",
        "expires_utc": "2026-08-12T12:30:10+00:00",
    }
    for field, value in invalid_mutations.items():
        mutated = example()
        provider_mutated = first_provider_bound_artifact(mutated)[
            "provider_binding"
        ]
        assert isinstance(provider_mutated, dict)
        provider_mutated[field] = value
        assert_invalid(mutated)

    mutated = example()
    provider_mutated = first_provider_bound_artifact(mutated)[
        "provider_binding"
    ]
    assert isinstance(provider_mutated, dict)
    provider_mutated["provider_sha256"] = None
    provider_mutated["provider_size_bytes"] = None
    provider_mutated["created_utc"] = None
    provider_mutated["expires_utc"] = None
    provider_mutated["downloaded_sha256_matches"] = None
    provider_mutated["downloaded_size_matches"] = None
    validate(mutated)


def test_artifact_record_contract_is_content_addressed_and_verified() -> None:
    packet = example()
    packet["artifacts"] = []
    assert_invalid(packet)

    required_fields = tuple(schema()["$defs"]["artifact_record"]["required"])
    for field in required_fields:
        packet = example()
        del packet["artifacts"][0][field]
        assert_invalid(packet)

    invalid_mutations = {
        "artifact_id": "not-an-artifact-id",
        "role": "unknown_role",
        "content_kind": "directory",
        "media_type": "",
        "member_path": "../escape.json",
        "display_path_or_uri": "",
        "sha256": "a" * 63,
        "size_bytes": -1,
        "digest_verified": False,
        "size_verified": False,
        "container_path_verified": False,
    }
    for field, value in invalid_mutations.items():
        packet = example()
        packet["artifacts"][0][field] = value
        assert_invalid(packet)

    packet = example()
    packet["artifacts"][0]["provider_binding"] = None
    validate(packet)


def test_role_binding_surface_is_complete_namespaced_and_unique() -> None:
    required_fields = tuple(schema()["$defs"]["role_bindings"]["required"])

    for field in required_fields:
        packet = example()
        del packet["role_bindings"][field]
        assert_invalid(packet)

    packet = example()
    packet["role_bindings"]["preservation_manifest"] = "not-an-artifact-id"
    assert_invalid(packet)

    for field in LIST_ROLE_BINDINGS:
        packet = example()
        values = packet["role_bindings"][field]
        assert values
        packet["role_bindings"][field] = [values[0], values[0]]
        assert_invalid(packet)


def test_complete_coverage_requires_complete_role_and_graph_state() -> None:
    for field in (
        "source_bindings_complete",
        "carrier_binding_complete",
        "artifact_graph_complete",
        "role_bindings_complete",
    ):
        packet = example()
        packet["coverage"][field] = False
        assert_invalid(packet)

    packet = example()
    packet["coverage"]["missing_roles"] = ["final_status"]
    assert_invalid(packet)

    packet = example()
    packet["coverage"]["unresolved_artifact_ids"] = [
        "artifact:unresolved"
    ]
    assert_invalid(packet)

    for field in CORE_SINGLETON_ROLE_BINDINGS:
        packet = example()
        packet["role_bindings"][field] = None
        assert_invalid(packet)

    packet = example()
    packet["role_bindings"]["candidate_records"] = []
    assert_invalid(packet)


def test_partial_and_unknown_coverage_can_truthfully_express_gaps() -> None:
    for coverage_status in ("partial", "unknown"):
        packet = example()
        packet["coverage"].update(
            {
                "artifact_graph_complete": False,
                "coverage_status": coverage_status,
                "missing_roles": ["final_status"],
                "role_bindings_complete": False,
                "source_bindings_complete": False,
                "unresolved_artifact_ids": ["artifact:unresolved"],
            }
        )
        packet["role_bindings"]["final_status"] = None
        packet["role_bindings"]["candidate_records"] = []
        validate(packet)


def test_coverage_counters_and_reference_lists_are_typed() -> None:
    counter_fields = (
        "artifacts_total",
        "provider_artifacts_total",
        "provider_artifacts_bound",
        "role_bindings_total",
        "role_bindings_resolved",
    )
    for field in counter_fields:
        packet = example()
        packet["coverage"][field] = -1
        assert_invalid(packet)

    packet = example()
    packet["coverage"]["missing_roles"] = [
        "final_status",
        "final_status",
    ]
    assert_invalid(packet)

    packet = example()
    packet["coverage"]["missing_roles"] = ["unknown_role"]
    assert_invalid(packet)

    packet = example()
    packet["coverage"]["unresolved_artifact_ids"] = [
        "artifact:unresolved",
        "artifact:unresolved",
    ]
    assert_invalid(packet)


def test_content_boundary_is_metadata_only_and_secret_free() -> None:
    locked = {
        "packet_payload_mode": "metadata_only",
        "artifact_bytes_embedded": False,
        "carrier_required_for_verification": True,
        "raw_secrets_included": False,
        "raw_model_inputs_included": False,
        "raw_model_outputs_included": False,
    }

    packet = example()
    assert packet["content_boundary"] == locked

    for field, expected in locked.items():
        packet = example()
        packet["content_boundary"][field] = (
            not expected if isinstance(expected, bool) else "embedded"
        )
        assert_invalid(packet)


def test_analysis_boundary_is_artifact_observed_and_non_runtime() -> None:
    locked = {
        "target_analysis_level": "artifact_observed",
        "runtime_observation_included": False,
        "runtime_observation_required_for_runtime_classification": True,
        "observer_in_subject_totals": False,
        "current_repository_state_substitution_allowed": False,
        "packet_is_compute_report": False,
        "packet_is_runtime_observation": False,
    }

    packet = example()
    assert packet["analysis_boundary"] == locked

    for field, expected in locked.items():
        packet = example()
        packet["analysis_boundary"][field] = (
            not expected if isinstance(expected, bool) else "runtime_observed"
        )
        assert_invalid(packet)


def test_authority_boundary_is_read_only_and_non_authorizing() -> None:
    packet = example()
    assert packet["authority_boundary"]["write_mode"] == (
        "subject_input_only"
    )

    packet["authority_boundary"]["write_mode"] = "apply"
    assert_invalid(packet)

    for field in LOCKED_FALSE_AUTHORITY_FIELDS:
        packet = example()
        assert packet["authority_boundary"][field] is False
        packet["authority_boundary"][field] = True
        assert_invalid(packet)


def test_ok_and_errors_are_coupled() -> None:
    packet = example()
    packet["ok"] = False
    packet["errors"] = ["synthetic_contract_error"]
    validate(packet)

    packet = example()
    packet["ok"] = True
    packet["errors"] = ["unexpected"]
    assert_invalid(packet)

    packet = example()
    packet["ok"] = False
    packet["errors"] = []
    assert_invalid(packet)

    packet = example()
    packet["ok"] = False
    packet["errors"] = [""]
    assert_invalid(packet)


def test_safe_member_paths_reject_absolute_backslash_and_dot_segments() -> None:
    mutations = (
        ("fixture_provenance", "fixture_source_path"),
        ("subject", "workflow_path"),
        ("carrier", "root_prefix"),
    )
    unsafe_values = (
        "/absolute/path",
        r"windows\path",
        "../escape",
        "nested/./member",
    )

    for section, field in mutations:
        for value in unsafe_values:
            packet = example()
            packet[section][field] = value
            assert_invalid(packet), (section, field, value)

    for value in unsafe_values:
        packet = example()
        packet["artifacts"][0]["member_path"] = value
        assert_invalid(packet), value


def test_required_exact_hashes_are_lowercase_hex() -> None:
    mutations = (
        ("subject", "source_commit", "A" * 40),
        ("subject", "policy_sha256", "A" * 64),
        ("carrier", "sha256", "A" * 64),
        ("authority_sources", "workflow", "sha256", "A" * 64),
    )

    for mutation in mutations:
        packet = example()
        if len(mutation) == 3:
            section, field, value = mutation
            packet[section][field] = value
        else:
            section, subsection, field, value = mutation
            packet[section][subsection][field] = value
        assert_invalid(packet), mutation


def test_schema_definition_surface_preserves_the_provenance_split() -> None:
    defs = schema()["$defs"]

    assert defs["producer"]["properties"]["production_mode"]["enum"] == [
        "current_run_export",
        "post_run_export",
        "fixed_source_adapter",
    ]
    assert defs["fixture_provenance"]["properties"][
        "source_data_status"
    ]["enum"] == [
        "historical_observed",
        "synthetic",
    ]
    assert defs["carrier"]["properties"]["carrier_kind"]["enum"] == [
        "preservation_archive",
        "current_run_export_archive",
        "provider_artifact_archive",
        "example_archive",
    ]

    example_branch, observed_branch = schema()["oneOf"]
    assert example_branch["properties"]["producer"] is False
    assert example_branch["required"] == ["fixture_provenance"]
    assert observed_branch["properties"]["fixture_provenance"] is False
    assert observed_branch["required"] == ["producer"]
