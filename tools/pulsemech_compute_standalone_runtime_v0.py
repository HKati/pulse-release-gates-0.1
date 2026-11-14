#!/usr/bin/env python3
"""Offline standalone runtime profile, with explicit source-byte admission.

This module does not extend the historical packet schema or its CLI validator.
It projects their shared record vocabulary into a distinct, non-release profile
and reuses their semantic checks and the existing runtime graph index. No
workflow, job, release-candidate, policy or release-decision identity is invented.

``selected_sources`` must come from a separately selected input, not from the
runtime packet. Each entry contains path, source_revision, sha256, size_bytes
and immutable data bytes. The caller authenticates repository provenance when
needed; this module verifies agreement with the independently supplied bytes.
Neither digest agreement nor a recorded receipt authenticates physical execution
or makes this profile a release-authority input. A replay reconstructs the
private source admission from raw inputs; serialized index claims are not tokens.
"""
from __future__ import annotations

import copy
from functools import lru_cache
import os
from pathlib import Path
import stat
from typing import Any

import jsonschema

import check_pulsemech_compute_runtime_observation_packet_v0 as packet_validator
import pulsemech_compute_binding_analyzer_core_v0 as core


PROFILE = "standalone_operator_v0"
MAX_PACKET_BYTES = 2 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SCHEMA = ROOT / "schemas" / "pulsemech_compute_runtime_observation_packet_v0.schema.json"
RUNTIME_SCHEMA_SHA256 = "824991a9f5c21ca9bd9fd7d1fc5c5813af3ff0ef9714c8506d2c3e6a5f9fa0cc"
RUNTIME_SCHEMA_SIZE = 70467
RESOURCE_AXES = frozenset(packet_validator.RESOURCE_AXES)


class StandaloneError(ValueError):
    pass


StandaloneRuntimeError = StandaloneError


def _need(condition: bool, reason: str) -> None:
    if not condition:
        raise StandaloneError(reason)


@lru_cache(maxsize=1)
def _captured_runtime_schema() -> bytes:
    """Capture the installed, pinned verifier schema once, without a path reread."""
    try:
        _need(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_NONBLOCK"),
              "standalone_schema_safe_io_unsupported")
        descriptor = os.open(RUNTIME_SCHEMA, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            _need(stat.S_ISREG(before.st_mode) and before.st_size == RUNTIME_SCHEMA_SIZE,
                  "standalone_schema_not_selected_regular_file")
            data = stream.read(RUNTIME_SCHEMA_SIZE + 1)
            after = os.fstat(stream.fileno())
        _need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
              == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
              "standalone_schema_changed_during_capture")
        _need(len(data) == RUNTIME_SCHEMA_SIZE and core._runtime_sha(data) == RUNTIME_SCHEMA_SHA256,
              "standalone_schema_pin_mismatch")
        return data
    except OSError as exc:
        raise StandaloneError("standalone_schema_capture_failed") from exc


def standalone_schema() -> dict[str, Any]:
    """Return a narrow projection, leaving the selected legacy schema intact.

    The installed checker, this module and the reused validator/core form the
    trusted verification implementation. The installed legacy schema is captured
    once and checked against this version's immutable digest. These verification
    dependencies are separate from selected subject-execution sources.
    This projection is not accepted by the historical validator.
    """
    schema = copy.deepcopy(core._runtime_load(_captured_runtime_schema()))
    schema["$id"] = "urn:pulsemech:standalone-operator-runtime:v0"
    schema["title"] = "PULSEmech standalone operator runtime v0"
    schema["required"].append("packet_profile")
    schema["properties"]["packet_profile"] = {"const": PROFILE}
    defs = schema["$defs"]
    fields = {
        "subject_profile": {"const": PROFILE},
        "repository": {"$ref": "#/$defs/non_empty_string"},
        "source_commit": {"$ref": "#/$defs/sha40"},
        "acquisition_id": {"$ref": "#/$defs/non_empty_string"},
        "acquisition_attempt": {"type": "integer", "const": 1},
        "subject_run_key": {"$ref": "#/$defs/non_empty_string"},
        "protocol_id": {"$ref": "#/$defs/non_empty_string"},
        "selection_sha256": {"$ref": "#/$defs/sha256"},
        "release_candidate_id": {"type": "null"},
        "run_mode": {"const": "standalone_operator"},
        "active_policy_sets": {"type": "array", "maxItems": 0},
    }
    defs["subject"] = {"type": "object", "additionalProperties": False,
                       "required": list(fields), "properties": fields}
    defs["authority_inputs"] = {"type": "object", "maxProperties": 0}
    defs["producer"]["properties"]["ci_workflow_or_job_identity"] = {"type": "null"}
    defs["producer"]["properties"]["collection_mode"] = {"enum": ["example", "tool_wrapper"]}
    defs["packet_identity"]["properties"].update({
        "packet_sequence": {"const": 0}, "previous_packet_sha256": {"type": "null"},
        "packet_scope": {"enum": ["example", "subject_run"]},
    })
    defs["observation_boundary"]["properties"]["collector_mode"] = {"enum": ["example", "tool_wrapper"]}
    execution = defs["execution_record"]
    for key in ("workflow_name", "job_name", "job_id", "job_attempt", "step_name", "step_number", "parent_execution_id"):
        execution["properties"][key] = {"type": "null"}
    execution["properties"]["execution_scope"] = {"enum": ["subject", "observation_collector"]}
    execution["properties"]["permitted_mutation_authority"] = {"const": "advisory_output"}
    execution["allOf"].append({
        "if": {"properties": {"execution_scope": {"const": "subject"}}, "required": ["execution_scope"]},
        "then": {"properties": {"execution_kind": {"const": "local_tool_execution"},
                                  "declared_role": {"const": "transition"},
                                  "input_state_ids": {"minItems": 1, "maxItems": 1}}},
    })
    defs["source_identity"]["properties"].update({
        "source_kind": {"const": "repository_file"}, "identity_status": {"const": "exact"},
        "action_repository": {"type": "null"}, "action_ref": {"type": "null"},
        "action_commit_sha": {"type": "null"}, "container_image_digest": {"type": "null"},
    })
    defs["state_observation"]["properties"].update({
        "state_type": {"const": "other"}, "release_candidate_id": {"type": "null"},
        "authority_bearing": {"const": False},
        "mutation_class": {"enum": ["none", "advisory_output"]},
    })
    for key in ("external_calls", "model_inferences", "resource_measurements"):
        schema["properties"][key]["maxItems"] = 0
    for key in ("external_call_ids", "model_inference_ids", "resource_measurement_ids"):
        execution["properties"][key]["maxItems"] = 0
    schema["properties"]["executions"]["maxItems"] = 25
    schema["properties"]["state_observations"]["maxItems"] = 256
    defs["coverage"]["properties"]["coverage_status"] = {"const": "partial"}
    schema["properties"]["ok"] = {"const": True}
    jsonschema.Draft202012Validator.check_schema(schema)
    return schema


def _semantic_checks(packet: dict[str, Any]) -> None:
    # Apply the common checker to the actual standalone input. Its sole
    # release-specific requirement is replaced explicitly, without manufacturing
    # authority records or modifying the historical validator's input/output.
    checks, errors = packet_validator.semantic_checks(packet)
    checks.pop("authority_input_bindings_ok", None)
    errors = [error for error in errors if error != "check_failed: authority_input_bindings_ok"]
    _need(all(checks.values()) and not errors, "standalone_runtime_semantics:" + ";".join(errors))
    _need(packet["authority_inputs"] == {}, "standalone_authority_inputs_forbidden")
    subject = packet["subject"]
    _need(subject["release_candidate_id"] is None and subject["active_policy_sets"] == [],
          "standalone_authority_context_forbidden")
    collectors = [row for row in packet["executions"] if row["execution_scope"] == "observation_collector"]
    _need(len(collectors) == 1, "standalone_one_collector_required")
    collector = collectors[0]
    _need(collector["run_binding"]["execution_run_key"] != subject["subject_run_key"],
          "standalone_collector_run_must_be_separate")
    _need(collector["input_state_ids"] == [] and collector["output_state_ids"] == [],
          "standalone_collector_cannot_supply_subject_states")
    _need(all(row["source_identity"]["source_revision"] == subject["source_commit"]
              for row in packet["executions"]), "standalone_execution_revision_mismatch")
    _need(all(row["release_candidate_id"] is None and row["authority_bearing"] is False
              for row in packet["state_observations"]), "standalone_state_authority_forbidden")


def validate_and_index(
    runtime_bytes: bytes, *, expected_subject: dict[str, Any],
    selected_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate truthful standalone packet bytes and reuse the shared index.

    This checks the explicit standalone profile only. Historical CLI validators
    intentionally continue to reject it. Source admission establishes exact
    agreement with independently supplied bytes; source trust, carrier/state
    byte verification, acquisition receipts and protocol occurrence binding are
    separate obligations of the source-bound adapter that calls this function.
    """
    _need(type(runtime_bytes) is bytes and 0 < len(runtime_bytes) <= MAX_PACKET_BYTES,
          "standalone_runtime_bytes_invalid")
    try:
        packet = core._runtime_load(runtime_bytes)
        _need(packet.get("packet_profile") == PROFILE, "standalone_runtime_profile_required")
        _need(core._runtime_subject(expected_subject).get("subject_profile") == PROFILE,
              "standalone_expected_subject_required")
        _need(packet.get("subject") == expected_subject, "standalone_runtime_subject_mismatch")
        errors = packet_validator.schema_errors(standalone_schema(), packet)
        _need(not errors, "standalone_runtime_schema:" + ";".join(errors))
        _semantic_checks(packet)
        return core.index_runtime_packet_sources(
            [core.RuntimePacketSource("sha256:" + core._runtime_sha(runtime_bytes), runtime_bytes)],
            expected_subject=expected_subject, expected_authority_inputs={},
            standalone_source_bindings=selected_sources,
        )
    except core.RuntimeIndexError as exc:
        raise StandaloneRuntimeError(str(exc)) from exc
