#!/usr/bin/env python3
"""Check a finite required-gate suite declaration against caller-selected bytes.

This offline structural checker never runs an operator, interprets metric
semantics, authenticates a source, or grants execution/release authority. An
accepted ``complete`` record is only a complete declaration. The external
selection SHA-256 is mandatory and is never inferred from untrusted inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import sys
from typing import Any

import jsonschema
import yaml

SCHEMA_PATH = "schemas/required_gate_suite_contract_v0.schema.json"
CHECKER_PATH = "tools/check_required_gate_suite_contract_v0.py"
SCHEMA_SHA256 = "66df57c8ecbdc137b376fbab5248c395bdda47e3094b7cee74e4606ca825d215"
SUBJECT_SCHEMA_PATH = "schemas/pulsemech_compute_subject_input_packet_v0.schema.json"
RUNTIME_SCHEMA_PATH = "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json"
SUBJECT_SCHEMA_SHA256 = "8116c757ba7ee65c14ae159fe9969bc2084fe105b0df7e69ebee64f65b45f1e5"
RUNTIME_SCHEMA_SHA256 = "824991a9f5c21ca9bd9fd7d1fc5c5813af3ff0ef9714c8506d2c3e6a5f9fa0cc"
CORE_PATHS = {
    "contract_schema": SCHEMA_PATH,
    "checker_source": CHECKER_PATH,
    "policy": "pulse_gate_policy_v0.yml",
    "registry": "pulse_gate_registry_v0.yml",
    "subject_schema": SUBJECT_SCHEMA_PATH,
    "runtime_schema": RUNTIME_SCHEMA_PATH,
}
MATERIAL_ROLES = (
    "protocol", "operator", "comparison", "privacy", "observation_mapping",
    "subject_packet", "runtime_packet",
)
UNRESOLVED_ROLE = {
    "protocol": "protocol", "operator": "operator", "comparison": "comparison",
    "privacy": "privacy_retention", "observation_mapping": "observation_mapping",
    "subject_packet": "subject", "runtime_packet": "runtime_evidence",
}
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_FILES = 300
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 100000
DENIED_OUTPUT_NAMES = {"status.json", "release_decision_v0.json", "release_authority_v0.json"}
BOUNDARY = {
    "execution_ready": False,
    "execution_authorized": False,
    "semantic_verification": "not_run",
    "packet_semantics_verified": False,
    "metric_pass": None,
    "production_gate_eligible": False,
    "authority_effect": "none",
    "anchor_authentication": "not_established",
}
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_PATH = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\Z")
_StrictValidator = jsonschema.validators.extend(
    jsonschema.Draft202012Validator,
    type_checker=jsonschema.Draft202012Validator.TYPE_CHECKER.redefine(
        "integer", lambda checker, value: type(value) is int
    ),
)


class ContractError(ValueError):
    """A stable diagnostic code that never includes private input content."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise ContractError(code)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    """Deterministic UTF-8 JSON; no time, paths, or environmental fields."""
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ContractError("canonicalization_failed") from exc


def _bounded_values(value: Any) -> None:
    stack = [(value, 0)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        _need(depth <= MAX_JSON_DEPTH and count <= MAX_JSON_NODES, "document_complexity_limit")
        if isinstance(item, float):
            _need(math.isfinite(item), "nonfinite_number")
        elif isinstance(item, str):
            _need(not any(0xD800 <= ord(ch) <= 0xDFFF for ch in item), "invalid_unicode")
        elif isinstance(item, dict):
            _need(all(isinstance(key, str) for key in item), "mapping_key_type")
            stack.extend((key, depth + 1) for key in item)
            stack.extend((entry, depth + 1) for entry in item.values())
        elif isinstance(item, list):
            stack.extend((entry, depth + 1) for entry in item)
        else:
            _need(item is None or type(item) in (bool, int), "document_value_type")


def _json(raw: bytes) -> dict[str, Any]:
    def pairs(entries):
        result = {}
        for key, value in entries:
            _need(key not in result, "json_duplicate_key")
            result[key] = value
        return result

    def nonfinite(_):
        raise ContractError("nonfinite_number")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("json_syntax") from exc
    _bounded_values(value)  # Also catches exponent overflow such as 1e999.
    _need(isinstance(value, dict), "json_object_required")
    return value


class _UniqueLoader(yaml.SafeLoader):
    def compose_node(self, parent, index):
        # Alias expansion must be refused before construction and size checks.
        _need(not self.check_event(yaml.AliasEvent), "yaml_alias_forbidden")
        return super().compose_node(parent, index)


def _yaml_mapping(loader, node, deep=False):
    # These selected source files need no merge keys. Never flatten mappings:
    # nested merges can expand before post-parse complexity limits run.
    _need(all(key.tag != "tag:yaml.org,2002:merge" for key, _ in node.value),
          "yaml_merge_forbidden")
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        _need(isinstance(key, str), "mapping_key_type")
        _need(key not in result, "yaml_duplicate_key")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _yaml_mapping)


def _yaml(raw: bytes) -> dict[str, Any]:
    try:
        value = yaml.load(raw.decode("utf-8"), Loader=_UniqueLoader)
    except (yaml.YAMLError, UnicodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("yaml_syntax") from exc
    _bounded_values(value)
    _need(isinstance(value, dict), "yaml_object_required")
    return value


def _supported_platform() -> None:
    _need(os.name == "posix"
          and all(hasattr(os, flag) for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK", "O_CLOEXEC"))
          and all(operation in os.supports_dir_fd for operation in (os.open, os.stat, os.link, os.unlink)),
          "platform_not_supported")


def _absolute(path: str | Path) -> Path:
    try:
        result = Path(os.path.abspath(os.fspath(path)))
    except (TypeError, ValueError, OSError) as exc:
        raise ContractError("path_invalid") from exc
    _need("\x00" not in str(result), "path_invalid")
    return result


def _parent_fd(path: Path) -> tuple[int, str]:
    """Open every directory by descriptor; never follow a symlink component."""
    parts = path.parts
    _need(path.is_absolute() and len(parts) > 1, "path_invalid")
    fd = None
    try:
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        for part in parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=fd)
            os.close(fd)
            fd = child
        return fd, parts[-1]
    except (OSError, ValueError) as exc:
        if fd is not None:
            os.close(fd)
        raise ContractError("unsafe_or_missing_path") from exc


def _read_regular(path: Path) -> bytes:
    parent, name = _parent_fd(path)
    fd = None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                     dir_fd=parent)
        before = os.fstat(fd)
        _need(stat.S_ISREG(before.st_mode), "file_not_regular")
        _need(0 < before.st_size <= MAX_FILE_BYTES, "file_size_limit")
        chunks = []
        total = 0
        while True:
            chunk = os.read(fd, min(65536, MAX_FILE_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            _need(total <= MAX_FILE_BYTES, "file_size_limit")
        after = os.fstat(fd)
        identity = lambda st: (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
        _need(identity(before) == identity(after) and total == before.st_size, "file_changed_during_read")
        return b"".join(chunks)
    except (OSError, ValueError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("file_read_failed") from exc
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


class _Reader:
    def __init__(self, root: str | Path):
        self.root = _absolute(root)
        # Check root itself, even before the first selected binding is opened.
        parent, name = _parent_fd(self.root)
        fd = None
        try:
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                         dir_fd=parent)
        except OSError as exc:
            raise ContractError("root_not_safe_directory") from exc
        finally:
            if fd is not None:
                os.close(fd)
            os.close(parent)
        self.cache: dict[Path, bytes] = {}
        self.total = 0

    def read(self, path: str | Path) -> bytes:
        absolute = _absolute(path)
        if absolute not in self.cache:
            _need(len(self.cache) < MAX_FILES, "file_count_limit")
            raw = _read_regular(absolute)
            self.total += len(raw)
            _need(self.total <= MAX_TOTAL_BYTES, "total_byte_limit")
            self.cache[absolute] = raw
        return self.cache[absolute]

    def selected_path(self, relative: str) -> Path:
        _need(isinstance(relative, str) and len(relative) <= 400 and bool(_PATH.fullmatch(relative)),
              "binding_path_invalid")
        _need(all(part not in (".", "..") for part in relative.split("/")), "binding_path_invalid")
        return self.root / relative

    def binding(self, reference: dict[str, Any]) -> bytes:
        _need(type(reference["size_bytes"]) is int, "binding_size_type")
        raw = self.read(self.selected_path(reference["path"]))
        _need(len(raw) == reference["size_bytes"], "binding_size_mismatch")
        _need(_sha(raw) == reference["sha256"], "binding_digest_mismatch")
        return raw


def _local_schema(schema: dict[str, Any]) -> None:
    stack = [(schema, True)]
    while stack:
        item, is_root = stack.pop()
        if isinstance(item, dict):
            _need(is_root or "$id" not in item, "nested_schema_id")
            for key in ("$ref", "$dynamicRef", "$recursiveRef"):
                if key in item:
                    _need(isinstance(item[key], str) and item[key].startswith("#"), "remote_schema_reference")
            stack.extend((value, False) for value in item.values())
        elif isinstance(item, list):
            stack.extend((value, False) for value in item)


def _validate_schema(value: Any, schema: dict[str, Any], code: str, definition: str | None = None) -> None:
    _local_schema(schema)
    target = schema if definition is None else {
        "$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/" + definition,
    }
    try:
        _StrictValidator.check_schema(target)
        validator = _StrictValidator(target, format_checker=jsonschema.FormatChecker())
        _need(next(validator.iter_errors(value), None) is None, code)
    except jsonschema.exceptions.SchemaError as exc:
        raise ContractError("schema_definition_invalid") from exc


def _index(items: list[dict[str, Any]], key: str, code: str) -> dict[str, dict[str, Any]]:
    identifiers = [item[key] for item in items]
    _need(len(identifiers) == len(set(identifiers)), code)
    return dict(zip(identifiers, items))


def _check_roster(cases, occurrences, obligations, gates, inputs, *, complete: bool):
    case_map = _index(cases, "case_id", "duplicate_case_id")
    occurrence_map = _index(occurrences, "occurrence_id", "duplicate_occurrence_id")
    obligation_map = _index(obligations, "obligation_id", "duplicate_obligation_id")
    _need(all(case["input_id"] in inputs for case in cases), "case_input_unknown")
    variants = set()
    for case in cases:
        baseline = case["baseline_case_id"]
        variant = case["variant_id"]
        _need((baseline is None) == (variant is None), "variant_binding_invalid")
        if baseline is not None:
            _need(baseline in case_map and baseline != case["case_id"], "baseline_case_unknown")
            original = case_map[baseline]
            _need(original["baseline_case_id"] is None, "baseline_must_not_be_variant")
            key = (baseline, variant)
            _need(key not in variants, "duplicate_variant_id")
            variants.add(key)
            _need(inputs[case["input_id"]]["sha256"] != inputs[original["input_id"]]["sha256"],
                  "baseline_variant_input_alias")
    for occurrence in occurrences:
        _need(occurrence["case_id"] in case_map, "occurrence_case_unknown")
    covered_cases, covered_occurrences, covered_gates = set(), set(), set()
    for obligation in obligations:
        _need(obligation["gate_id"] in gates, "obligation_gate_unselected")
        _need(set(obligation["case_ids"]) <= case_map.keys(), "obligation_case_unknown")
        _need(set(obligation["occurrence_ids"]) <= occurrence_map.keys(), "obligation_occurrence_unknown")
        occurrence_cases = {occurrence_map[key]["case_id"] for key in obligation["occurrence_ids"]}
        _need(occurrence_cases == set(obligation["case_ids"]), "obligation_case_occurrence_mismatch")
        covered_cases.update(obligation["case_ids"])
        covered_occurrences.update(obligation["occurrence_ids"])
        covered_gates.add(obligation["gate_id"])
    if complete:
        _need(bool(cases and occurrences and obligations and inputs), "complete_inventory_empty")
        _need(covered_gates == set(gates), "gate_obligation_missing")
        _need(covered_cases == case_map.keys(), "case_obligation_missing")
        _need(covered_occurrences == occurrence_map.keys(), "occurrence_obligation_missing")
        _need({item["case_id"] for item in occurrences} == case_map.keys(), "case_occurrence_missing")
        _need({item["input_id"] for item in cases} == inputs.keys(), "input_unused")
    return case_map, occurrence_map, obligation_map


def _protocol_roster(contract, protocol, inputs, complete: bool) -> None:
    for key in ("origin", "source", "suite_id", "selected_gate_ids"):
        _need(contract[key] == protocol[key], "protocol_identity_mismatch")
    _check_roster(protocol["cases"], protocol["expected_occurrences"], protocol["obligations"],
                  protocol["selected_gate_ids"], inputs, complete=True)
    actual_occurrences = [{"occurrence_id": item["occurrence_id"], "case_id": item["case_id"]}
                          for item in contract["occurrences"]]
    for actual, expected, key, code in (
        (contract["cases"], protocol["cases"], "case_id", "protocol_case_mismatch"),
        (actual_occurrences, protocol["expected_occurrences"], "occurrence_id", "protocol_occurrence_mismatch"),
        (contract["obligations"], protocol["obligations"], "obligation_id", "protocol_obligation_mismatch"),
    ):
        actual_map = {item[key]: item for item in actual}
        expected_map = {item[key]: item for item in expected}
        _need(all(expected_map.get(identifier) == item for identifier, item in actual_map.items()), code)
        if complete:
            _need(actual_map == expected_map, code)


def _packet_origin(packet, origin: str, *, subject: bool) -> None:
    synthetic = packet.get("fixture_provenance", {}).get("source_data_status") == "synthetic"
    if origin == "synthetic_fixture":
        _need(packet["record_status"] == "example", "synthetic_packet_promoted")
        if subject:
            _need(synthetic, "synthetic_origin_missing")
    else:
        _need(not synthetic and packet["record_status"] == "observed", "synthetic_origin_promotion")


def _packet_subject(packet, source) -> None:
    subject = packet["subject"]
    _need(subject["repository"] == source["repository"] and subject["source_commit"] == source["commit"],
          "packet_source_mismatch")
    _need(packet["packet_identity"]["subject_run_key"] == subject["subject_run_key"],
          "packet_run_identity_mismatch")


def _compare_subjects(subject_packet, runtime_packet) -> None:
    left, right = subject_packet["subject"], runtime_packet["subject"]
    for key in ("repository", "source_commit", "source_ref", "subject_run_key", "workflow_name",
                "workflow_run_id", "workflow_run_number", "workflow_run_attempt", "release_candidate_id",
                "event_name", "run_mode"):
        _need(left[key] == right[key], "packet_subject_mismatch")
    _need(set(left["active_policy_sets"]) == set(right["active_policy_sets"]), "packet_subject_mismatch")


def _packet_references(contract, subject_packet, runtime_packet, inputs, operator) -> None:
    _compare_subjects(subject_packet, runtime_packet)
    right = runtime_packet["subject"]
    executions = _index(runtime_packet["executions"], "execution_id", "duplicate_execution_id")
    states = _index(runtime_packet["state_observations"], "state_id", "duplicate_state_id")
    selected = [item["execution_id"] for item in contract["occurrences"]]
    _need(len(selected) == len(set(selected)), "execution_reused_for_occurrence")
    case_map = {item["case_id"]: item for item in contract["cases"]}
    for occurrence in contract["occurrences"]:
        _need(occurrence["packet_id"] == runtime_packet["packet_identity"]["packet_id"], "packet_id_mismatch")
        _need(occurrence["execution_id"] in executions, "execution_unknown")
        execution = executions[occurrence["execution_id"]]
        _need(execution["execution_scope"] == "subject"
              and execution["declared_role"] != "observer"
              and execution["execution_kind"] != "observer_execution", "execution_not_subject")
        binding = execution["run_binding"]
        _need(binding["execution_run_key"] == right["subject_run_key"]
              and binding["subject_run_key"] == right["subject_run_key"]
              and binding["binding_mode"] == "current_subject_run"
              and binding["binding_complete"] is True, "execution_run_mismatch")
        identity = execution["source_identity"]
        _need(identity["source_kind"] == "repository_file" and identity["identity_status"] == "exact"
              and identity["source_path_or_uri"] == operator["path"]
              and identity["source_sha256"] == operator["sha256"]
              and identity["source_revision"] == contract["source"]["commit"], "execution_operator_mismatch")
        for edge in ("input_state_ids", "output_state_ids"):
            _need(occurrence[edge] == execution[edge], "execution_state_edges_mismatch")
            _need(len(execution[edge]) == len(set(execution[edge])), "duplicate_execution_state_edge")
            for identifier in occurrence[edge]:
                _need(identifier in states, "state_unknown")
                state = states[identifier]
                _need(state["subject_run_key"] == right["subject_run_key"], "state_run_mismatch")
                _need(state["release_candidate_id"] == right["release_candidate_id"], "state_candidate_mismatch")
                if edge == "output_state_ids":
                    _need(state["producer_execution_id"] == execution["execution_id"], "state_output_producer_mismatch")
        input_reference = inputs[case_map[occurrence["case_id"]]["input_id"]]
        # Each occurrence must consume its case input, including repeated cases.
        _need(any(states[identifier]["content_status"] == "exact_digest"
                  and states[identifier]["sha256"] == input_reference["sha256"]
                  and states[identifier]["size_bytes"] == input_reference["size_bytes"]
                  for identifier in occurrence["input_state_ids"]),
              "case_input_digest_mismatch")


def _base_report() -> dict[str, Any]:
    return {
        "record_type": "required_gate_suite_contract_validation_v0",
        "valid": False, "declaration_state": None, "declaration_complete": False,
        "origin": None, "selection_sha256": None, "contract_sha256": None,
        "counts": {"selected_gates": 0, "cases": 0, "occurrences": 0, "obligations": 0, "inputs": 0},
        "unresolved_decisions": [], "errors": [], **BOUNDARY,
    }


def rejection_report(code: str) -> dict[str, Any]:
    """Return a content-free report for one coded validation failure."""
    report = _base_report()
    report["errors"] = [code]
    return report


def validate_contract(contract_path: str | Path, selection_path: str | Path,
                      selection_sha256: str, root: str | Path) -> dict[str, Any]:
    """Validate selected bytes; raise ContractError without echoing source data.

    The caller is responsible for choosing ``selection_sha256`` independently.
    An accepted record does not authenticate that choice or execute a suite.
    """
    _supported_platform()
    _need(isinstance(selection_sha256, str) and bool(_HEX.fullmatch(selection_sha256)), "selection_hash_required")
    reader = _Reader(root)
    selection_raw = reader.read(selection_path)
    _need(_sha(selection_raw) == selection_sha256, "selection_hash_mismatch")
    selection = _json(selection_raw)
    schema_raw = reader.read(reader.selected_path(SCHEMA_PATH))
    _need(_sha(schema_raw) == SCHEMA_SHA256, "contract_schema_identity_mismatch")
    schema = _json(schema_raw)
    _validate_schema(selection, schema, "selection_schema_invalid", "selection")
    for role, expected in CORE_PATHS.items():
        _need(selection["bindings"][role]["path"] == expected, "core_binding_path_mismatch")
    _need(_absolute(contract_path) == reader.selected_path(selection["contract"]["path"]), "contract_path_mismatch")
    contract_raw = reader.binding(selection["contract"])
    contract = _json(contract_raw)
    _validate_schema(contract, schema, "contract_schema_invalid")
    complete = contract["declaration_state"] == "complete"
    for key in ("origin", "source", "selected_gate_ids"):
        _need(contract[key] == selection[key], "selection_contract_identity_mismatch")
    material = selection["bindings"]
    bound = {}
    for role, reference in material.items():
        if reference is not None:
            bound[role] = reader.binding(reference)
    _need(_sha(bound["checker_source"]) == _sha(reader.read(_absolute(__file__))), "executing_checker_identity_mismatch")
    _need(_sha(bound["contract_schema"]) == SCHEMA_SHA256, "contract_schema_identity_mismatch")
    _need(_sha(bound["subject_schema"]) == SUBJECT_SCHEMA_SHA256, "subject_schema_identity_mismatch")
    _need(_sha(bound["runtime_schema"]) == RUNTIME_SCHEMA_SHA256, "runtime_schema_identity_mismatch")
    for role in MATERIAL_ROLES:
        digest = None if material[role] is None else material[role]["sha256"]
        _need(contract["binding_sha256"][role] == digest, "contract_binding_mismatch")
        if material[role] is None:
            _need(not complete and UNRESOLVED_ROLE[role] in contract["unresolved_decisions"],
                  "unresolved_binding_missing")
    inputs = _index(selection["inputs"], "input_id", "duplicate_input_id")
    for reference in inputs.values():
        reader.binding(reference)
    policy, registry = _yaml(bound["policy"]), _yaml(bound["registry"])
    required = policy.get("gates", {}).get("required") if isinstance(policy.get("gates"), dict) else None
    known = registry.get("gates")
    _need(isinstance(required, list) and all(isinstance(gate, str) for gate in required)
          and len(required) == len(set(required)) and isinstance(known, dict), "policy_registry_shape")
    _need(set(selection["selected_gate_ids"]) <= set(required)
          and set(selection["selected_gate_ids"]) <= known.keys(), "gate_not_required_and_registered")
    _check_roster(contract["cases"], contract["occurrences"], contract["obligations"],
                  contract["selected_gate_ids"], inputs, complete=complete)
    if not complete:
        unresolved = contract["unresolved_decisions"]
        if not contract["cases"] or not inputs:
            _need("cases" in unresolved, "unresolved_cases_missing")
        if not contract["occurrences"]:
            _need("runtime_evidence" in unresolved, "unresolved_runtime_missing")
        if {item["gate_id"] for item in contract["obligations"]} != set(contract["selected_gate_ids"]):
            _need("protocol" in unresolved, "unresolved_obligations_missing")
    if "protocol" in bound:
        protocol = _json(bound["protocol"])
        _validate_schema(protocol, schema, "protocol_schema_invalid", "protocol")
        _protocol_roster(contract, protocol, inputs, complete)
    subject_packet = runtime_packet = None
    if "subject_packet" in bound:
        subject_packet = _json(bound["subject_packet"])
        _validate_schema(subject_packet, _json(bound["subject_schema"]), "subject_packet_schema_invalid")
        # The bounded-reference schema branch has a different identity projection.
        # Supporting it needs an explicit adapter; never silently skip absent keys.
        _need("input_profile" not in subject_packet, "packet_profile_unsupported")
        _packet_origin(subject_packet, contract["origin"], subject=True)
        _packet_subject(subject_packet, contract["source"])
    if "runtime_packet" in bound:
        runtime_packet = _json(bound["runtime_packet"])
        _validate_schema(runtime_packet, _json(bound["runtime_schema"]), "runtime_packet_schema_invalid")
        _packet_origin(runtime_packet, contract["origin"], subject=False)
        _packet_subject(runtime_packet, contract["source"])
        # Reject duplicate packet IDs before any dictionary index can hide them.
        _index(runtime_packet["executions"], "execution_id", "duplicate_execution_id")
        _index(runtime_packet["state_observations"], "state_id", "duplicate_state_id")
    if contract["occurrences"]:
        _need(subject_packet is not None and runtime_packet is not None and material["operator"] is not None,
              "occurrence_packet_binding_missing")
    if subject_packet is not None and runtime_packet is not None:
        if contract["occurrences"]:
            _packet_references(contract, subject_packet, runtime_packet, inputs, material["operator"])
        else:
            # Both supplied packets must identify the same subject, even in a draft.
            _compare_subjects(subject_packet, runtime_packet)
    report = _base_report()
    report.update({
        "valid": True, "declaration_state": contract["declaration_state"],
        "declaration_complete": complete, "origin": contract["origin"],
        "selection_sha256": selection_sha256, "contract_sha256": _sha(contract_raw),
        "counts": {"selected_gates": len(contract["selected_gate_ids"]), "cases": len(contract["cases"]),
                   "occurrences": len(contract["occurrences"]), "obligations": len(contract["obligations"]),
                   "inputs": len(inputs)},
        "unresolved_decisions": sorted(contract["unresolved_decisions"]),
    })
    return report


def _output_preflight(path: str | Path) -> tuple[int, str]:
    _supported_platform()
    absolute = _absolute(path)
    _need(absolute.name.casefold() not in DENIED_OUTPUT_NAMES, "output_authority_name")
    try:
        parent, name = _parent_fd(absolute)
    except ContractError as exc:
        raise ContractError("output_unsafe_path") from exc
    try:
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return parent, name
        raise ContractError("output_exists")
    except (OSError, ContractError) as exc:
        os.close(parent)
        if isinstance(exc, ContractError):
            raise
        raise ContractError("output_unsafe_path") from exc


def _write_output(parent: int, name: str, raw: bytes) -> None:
    # Stage in the already opened directory, then link atomically without replacement.
    temporary = ".required-gate-report-" + secrets.token_hex(16)
    fd = None
    created = False
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=parent)
        created = True
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            _need(written > 0, "output_write_failed")
            offset += written
        os.fsync(fd)
        os.close(fd)
        fd = None
        os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
    except FileExistsError as exc:
        raise ContractError("output_exists") from exc
    except OSError as exc:
        raise ContractError("output_write_failed") from exc
    finally:
        if fd is not None:
            os.close(fd)
        if created:
            try:
                os.unlink(temporary, dir_fd=parent)
            except OSError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--selection-sha256", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    destination = None
    try:
        if args.out is not None:
            try:
                destination = _output_preflight(args.out)
            except ContractError as exc:
                sys.stdout.buffer.write(canonical_bytes(rejection_report(exc.code)))
                return 2
        try:
            report = validate_contract(args.contract, args.selection, args.selection_sha256, args.root)
            status = 0
        except ContractError as exc:
            report = rejection_report(exc.code)
            status = 1
        raw = canonical_bytes(report)
        if destination is not None:
            try:
                _write_output(*destination, raw)
            except ContractError as exc:
                sys.stdout.buffer.write(canonical_bytes(rejection_report(exc.code)))
                return 2
        sys.stdout.buffer.write(raw)
        return status
    finally:
        if destination is not None:
            os.close(destination[0])


if __name__ == "__main__":
    raise SystemExit(main())
