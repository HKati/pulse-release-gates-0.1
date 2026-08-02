#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any, Iterable

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check_pulsemech_compute_current_run_export_expectation_v0.py"
EXPECTATION_SCHEMA = ROOT / "schemas" / "pulsemech_compute_current_run_export_expectation_v0.schema.json"
EXPECTATION = ROOT / "examples" / "compute" / "pulsemech_compute_current_run_export_expectation_example_v0.json"
SUBJECT_INPUT_SCHEMA = ROOT / "schemas" / "pulsemech_compute_subject_input_packet_v0.schema.json"
TOOLS_TESTS_MANIFEST = ROOT / "ci" / "tools-tests.list"
TEST_RELATIVE_PATH = "tests/test_check_pulsemech_compute_current_run_export_expectation_v0.py"

EXPECTED_TOOL_LINES = 2426
EXPECTED_TOOL_BYTES = 80363
EXPECTED_TOOL_SHA256 = "61890497d680a0d6df1fc2e52fcd7522dca30d7ac8b36d4482e9de70befb2a35"
EXPECTED_TOOL_GIT_BLOB_SHA1 = "16b75b7df2524515146bf3472e0191a52cfad037"
EXPECTED_EXPECTATION_SCHEMA_GIT_BLOB_SHA1 = "c0bc5a21f5bf46c529341d2e805f26525c70c7f4"
EXPECTED_SUBJECT_INPUT_SCHEMA_GIT_BLOB_SHA1 = "e1f982ffaf900c6c17745624d80f9f38b374448b"
EXTERNAL_SCHEMA_URI = "https://127.0.0.1:9/pulsemech-forbidden-schema.json"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    framed = f"blob {len(payload)}\0".encode("ascii") + payload
    try:
        return hashlib.sha1(framed, usedforsecurity=False).hexdigest()
    except TypeError:
        return hashlib.sha1(framed).hexdigest()


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise ValueError(f"non-finite value: {value}")


def parse_json_text(text: str) -> dict[str, Any]:
    value = json.loads(
        text,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )
    assert isinstance(value, dict)
    return value


def load_json(path: Path) -> dict[str, Any]:
    return parse_json_text(path.read_text(encoding="utf-8"))


def render_json(value: Any) -> str:
    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_json(value), encoding="utf-8", newline="\n")


def import_tool_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "pulsemech_current_run_expectation_validator_v0_under_test",
        TOOL,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL_MODULE = import_tool_module()
_BASE_EXPECTATION = load_json(EXPECTATION)


def expectation() -> dict[str, Any]:
    return copy.deepcopy(_BASE_EXPECTATION)


def observed_expectation() -> dict[str, Any]:
    value = expectation()
    components = value["trusted_control_plane"]["components"]
    subject = value["subject"]
    builder = components["expectation_builder"]
    carrier_builder = components["carrier_loader"]

    value["record_status"] = "observed"
    value.pop("fixture_provenance")
    value["expectation_identity"]["expectation_scope"] = "current_run_export"
    value["expectation_producer"] = {
        "ci_workflow_or_job_identity": "PULSE CI / current-run expectation builder",
        "producer_id": "producer:current-run-expectation-builder/regression",
        "producer_name": "pulsemech-current-run-expectation-builder",
        "producer_run_key": subject["subject_run_key"],
        "producer_source": builder["path"],
        "producer_source_revision": builder["source_revision"],
        "producer_source_sha256": builder["sha256"],
        "producer_version": builder["version"],
        "production_mode": "current_run_expectation_builder",
    }
    value["carrier"]["carrier_kind"] = "current_run_export_archive"
    value["carrier"]["producer"] = {
        "ci_workflow_or_job_identity": "PULSE CI / current-run export carrier builder",
        "producer_id": "producer:current-run-export-carrier-builder/regression",
        "producer_name": "pulsemech-current-run-export-carrier-builder",
        "producer_run_key": subject["subject_run_key"],
        "producer_source": carrier_builder["path"],
        "producer_source_revision": carrier_builder["source_revision"],
        "producer_source_sha256": carrier_builder["sha256"],
        "producer_version": carrier_builder["version"],
        "production_mode": "current_run_export_carrier_builder",
    }
    return value


def run_tool(
    *,
    tool: Path = TOOL,
    schema_path: Path = EXPECTATION_SCHEMA,
    expectation_path: Path = EXPECTATION,
    subject_input_schema_path: Path = SUBJECT_INPUT_SCHEMA,
    repository_root: Path = ROOT,
    output: Path | None = None,
    extra_env: dict[str, str] | None = None,
    remove_env: Iterable[str] = (),
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(tool),
        "--schema",
        str(schema_path),
        "--expectation",
        str(expectation_path),
        "--subject-input-schema",
        str(subject_input_schema_path),
        "--repository-root",
        str(repository_root),
    ]
    if output is not None:
        command.extend(["--output", str(output)])

    environment = dict(os.environ)
    for key in remove_env:
        environment.pop(key, None)
    if extra_env:
        environment.update(extra_env)

    return subprocess.run(
        command,
        cwd=repository_root if repository_root.is_dir() else ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=environment,
    )


def diagnostic_from_result(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    streams = [stream for stream in (result.stdout, result.stderr) if stream]
    assert len(streams) == 1, (result.returncode, result.stdout, result.stderr)
    assert "Traceback" not in streams[0]
    return parse_json_text(streams[0])


def assert_validation_failure(
    result: subprocess.CompletedProcess[str],
    expected_fragment: str,
    *,
    expected_returncode: int | None = None,
) -> dict[str, Any]:
    assert result.returncode != 0, result.stdout + result.stderr
    if expected_returncode is not None:
        assert result.returncode == expected_returncode, result.stdout + result.stderr
    diagnostic = diagnostic_from_result(result)
    assert diagnostic["ok"] is False
    assert any(expected_fragment in str(error) for error in diagnostic["errors"]), diagnostic
    return diagnostic


def copy_contract_repository(tmp_path: Path) -> dict[str, Path]:
    replica = tmp_path / "repository"
    paths = {
        "root": replica,
        "tool": replica / "tools" / TOOL.name,
        "schema": replica / "schemas" / EXPECTATION_SCHEMA.name,
        "expectation": replica / "examples" / "compute" / EXPECTATION.name,
        "subject_schema": replica / "schemas" / SUBJECT_INPUT_SCHEMA.name,
    }
    for key, source in (
        ("tool", TOOL),
        ("schema", EXPECTATION_SCHEMA),
        ("expectation", EXPECTATION),
        ("subject_schema", SUBJECT_INPUT_SCHEMA),
    ):
        destination = paths[key]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return paths


def manifest_entries() -> list[str]:
    entries: list[str] = []
    for raw in TOOLS_TESTS_MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    return entries


def forbid_external_io(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    attempts: list[str] = []

    def forbidden(*args: Any, **_kwargs: Any) -> Any:
        attempts.append(repr(args))
        raise AssertionError("external I/O attempted")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    return attempts


# Artifact identity and tools-tests registration.

def test_validator_artifact_identity_matches_reviewed_merge() -> None:
    payload = TOOL.read_bytes()
    assert len(payload.splitlines()) == EXPECTED_TOOL_LINES
    assert len(payload) == EXPECTED_TOOL_BYTES
    assert sha256_bytes(payload) == EXPECTED_TOOL_SHA256
    assert git_blob_sha1(payload) == EXPECTED_TOOL_GIT_BLOB_SHA1
    assert payload.endswith(b"\n")
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert TOOL_MODULE.TOOL_NAME == "check_pulsemech_compute_current_run_export_expectation_v0"
    assert TOOL_MODULE.TOOL_VERSION == "0.1.0"


def test_reviewed_schema_blob_constants_match_canonical_bytes() -> None:
    expectation_blob = git_blob_sha1(EXPECTATION_SCHEMA.read_bytes())
    subject_blob = git_blob_sha1(SUBJECT_INPUT_SCHEMA.read_bytes())
    assert expectation_blob == EXPECTED_EXPECTATION_SCHEMA_GIT_BLOB_SHA1
    assert subject_blob == EXPECTED_SUBJECT_INPUT_SCHEMA_GIT_BLOB_SHA1
    assert TOOL_MODULE.CANONICAL_EXPECTATION_SCHEMA_GIT_BLOB_SHA1 == expectation_blob
    assert TOOL_MODULE.CANONICAL_SUBJECT_INPUT_SCHEMA_GIT_BLOB_SHA1 == subject_blob


def test_tools_tests_manifest_registers_regression_exactly_once() -> None:
    entries = manifest_entries()
    assert len(entries) == len(set(entries))
    assert entries.count(TEST_RELATIVE_PATH) == 1
    index = entries.index(TEST_RELATIVE_PATH)
    assert entries[index - 1] == "tests/test_pulsemech_compute_fixed_source_candidate_chain_v0.py"
    assert entries[index + 1] == "tests/test_pulsemech_compute_subject_input_packet_schema_v0.py"


# Canonical positive path and deterministic diagnostics.

def test_default_validation_is_deterministic_and_canonical() -> None:
    first = run_tool()
    second = run_tool()
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout
    diagnostic = parse_json_text(first.stdout)
    assert first.stdout == render_json(diagnostic)
    assert diagnostic["ok"] is True
    assert diagnostic["expectation_schema_valid"] is True
    assert diagnostic["expectation_schema_reference_policy_valid"] is True
    assert diagnostic["expectation_instance_valid"] is True
    assert diagnostic["subject_input_schema_valid"] is True
    assert diagnostic["subject_input_schema_reference_policy_valid"] is True
    assert diagnostic["subject_input_observed_branch_valid"] is True
    assert diagnostic["authority_effect"] == "none"
    assert diagnostic["errors"] == []
    assert diagnostic["checks"] and all(diagnostic["checks"].values())

    boundary = diagnostic["verification_boundary"]
    for key in (
        "supplied_contract_semantics_verified",
        "canonical_expectation_schema_path_verified",
        "canonical_expectation_schema_git_blob_verified",
        "canonical_subject_input_schema_path_verified",
        "canonical_subject_input_schema_git_blob_verified",
        "canonical_contract_semantics_verified",
        "contract_semantics_verified",
    ):
        assert boundary[key] is True
    assert boundary["external_schema_retrieval_allowed"] is False
    assert boundary["schema_reference_policy"] == "internal_fragment_only"
    assert boundary["carrier_bytes_verified"] is False
    assert boundary["control_plane_component_bytes_verified"] is False
    assert boundary["subject_authority_source_bytes_verified"] is False
    assert boundary["input_snapshot_mode"] == TOOL_MODULE._input_snapshot_mode()
    assert boundary["external_output_mode"] == TOOL_MODULE._external_output_mode()


def test_default_diagnostic_identifies_exact_consumed_bytes() -> None:
    result = run_tool()
    assert result.returncode == 0
    identities = parse_json_text(result.stdout)["input_identities"]
    for label, path in (
        ("expectation", EXPECTATION),
        ("expectation_schema", EXPECTATION_SCHEMA),
        ("subject_input_schema", SUBJECT_INPUT_SCHEMA),
    ):
        payload = path.read_bytes()
        assert identities[label]["sha256"] == sha256_bytes(payload)
        assert identities[label]["size_bytes"] == len(payload)
    assert identities["expectation_schema"]["git_blob_sha1"] == EXPECTED_EXPECTATION_SCHEMA_GIT_BLOB_SHA1
    assert identities["subject_input_schema"]["git_blob_sha1"] == EXPECTED_SUBJECT_INPUT_SCHEMA_GIT_BLOB_SHA1


def test_external_output_is_byte_identical_to_stdout(tmp_path: Path) -> None:
    output = tmp_path / "diagnostics" / "expectation-validator.json"
    result = run_tool(output=output)
    assert result.returncode == 0
    assert result.stderr == ""
    assert output.read_text(encoding="utf-8") == result.stdout


def test_platform_fallback_is_reported_as_weaker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(TOOL_MODULE, "_strict_descriptor_snapshot_available", lambda: False)
    monkeypatch.setattr(TOOL_MODULE, "_strict_output_descriptor_binding_available", lambda: False)
    diagnostic = TOOL_MODULE.make_diagnostic(
        ok=False,
        expectation_schema_valid=False,
        subject_input_schema_valid=False,
        record_status=None,
        checks={},
        derived={},
        input_identities={},
        errors=["synthetic"],
    )
    boundary = diagnostic["verification_boundary"]
    assert boundary["input_snapshot_mode"] == "path_identity_fallback"
    assert boundary["strict_descriptor_snapshot_verified"] is False
    assert boundary["external_output_mode"] == "path_atomic_replace_fallback"
    assert boundary["strict_output_descriptor_binding_available"] is False


# Strict input and output non-interference.

@pytest.mark.parametrize(
    ("payload", "fragment"),
    [
        (b"\xef\xbb\xbf{}\n", "UTF-8 BOM"),
        (b"{\xff}\n", "invalid UTF-8"),
        (b'{"record_status":"example","record_status":"observed"}\n', "duplicate JSON key"),
        (b'{"value": NaN}\n', "non-finite JSON value"),
        (b'{"broken": }\n', "invalid JSON"),
    ],
)
def test_strict_json_failures_are_machine_readable(tmp_path: Path, payload: bytes, fragment: str) -> None:
    path = tmp_path / "invalid-expectation.json"
    path.write_bytes(payload)
    diagnostic = assert_validation_failure(run_tool(expectation_path=path), fragment, expected_returncode=2)
    assert diagnostic["expectation_instance_valid"] is False


def test_noncanonical_expectation_bytes_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "noncanonical.json"
    path.write_text(json.dumps(expectation(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    diagnostic = assert_validation_failure(run_tool(expectation_path=path), "canonical_json_bytes_ok")
    assert diagnostic["expectation_schema_valid"] is True
    assert diagnostic["expectation_instance_valid"] is True
    assert diagnostic["checks"]["canonical_json_bytes_ok"] is False


def test_symlinked_expectation_input_is_rejected(tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlink support unavailable")
    alias = tmp_path / "expectation-link.json"
    try:
        alias.symlink_to(EXPECTATION)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    diagnostic = assert_validation_failure(run_tool(expectation_path=alias), "symlink", expected_returncode=2)
    assert diagnostic["ok"] is False


def test_repository_local_output_is_rejected_without_mutation() -> None:
    output = ROOT / "tests" / "out" / "current-run-expectation-diagnostic.json"
    output.unlink(missing_ok=True)
    result = run_tool(output=output)
    assert result.returncode == 2 and result.stdout == ""
    diagnostic = parse_json_text(result.stderr)
    assert any("output_inside_repository" in error for error in diagnostic["errors"])
    assert not output.exists()


def test_invalid_repository_root_fails_before_output(tmp_path: Path) -> None:
    output = ROOT / "tests" / "out" / "invalid-root-diagnostic.json"
    output.unlink(missing_ok=True)
    result = run_tool(repository_root=tmp_path / "missing-root", output=output)
    assert result.returncode == 2 and result.stdout == ""
    diagnostic = parse_json_text(result.stderr)
    assert any("repository_root" in error for error in diagnostic["errors"])
    assert not output.exists()


# Schema-reference policy and resolver backends.

@pytest.mark.parametrize(
    "schema_value",
    [
        {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "properties": {"$ref": {"type": "string"}}},
        {"$schema": "https://json-schema.org/draft/2020-12/schema", "const": {"$ref": EXTERNAL_SCHEMA_URI}},
        {"$schema": "https://json-schema.org/draft/2020-12/schema", "default": {"$dynamicRef": EXTERNAL_SCHEMA_URI}},
        {"$schema": "https://json-schema.org/draft/2020-12/schema", "examples": [{"$recursiveRef": EXTERNAL_SCHEMA_URI}]},
        {"$schema": "https://json-schema.org/draft/2020-12/schema", "enum": [{"$ref": EXTERNAL_SCHEMA_URI}]},
    ],
)
def test_reference_shaped_property_names_and_data_are_not_active(schema_value: dict[str, Any]) -> None:
    assert TOOL_MODULE.schema_reference_policy_errors(schema_value, label="probe") == []


@pytest.mark.parametrize(
    "schema_value",
    [
        {"$ref": EXTERNAL_SCHEMA_URI},
        {"allOf": [{"$ref": EXTERNAL_SCHEMA_URI}]},
        {"properties": {"value": {"$ref": EXTERNAL_SCHEMA_URI}}},
        {"$defs": {"value": {"$ref": EXTERNAL_SCHEMA_URI}}},
        {"items": {"$ref": EXTERNAL_SCHEMA_URI}},
        {"dependentSchemas": {"value": {"$ref": EXTERNAL_SCHEMA_URI}}},
        {"unevaluatedProperties": {"$ref": EXTERNAL_SCHEMA_URI}},
    ],
)
def test_external_references_in_schema_positions_are_rejected(schema_value: dict[str, Any]) -> None:
    errors = TOOL_MODULE.schema_reference_policy_errors(schema_value, label="probe")
    assert any("external_reference_not_permitted" in error for error in errors)


def test_internal_json_pointer_and_anchor_references_remain_valid() -> None:
    pointer_schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {"value": {"type": "string"}}, "$ref": "#/$defs/value"}
    escaped_pointer_schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {"a/b~c": {"type": "integer"}}, "$ref": "#/$defs/a~1b~0c"}
    anchor_schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {"value": {"$anchor": "target", "type": "string"}}, "$ref": "#target"}
    for value in (pointer_schema, escaped_pointer_schema, anchor_schema):
        assert TOOL_MODULE.schema_reference_policy_errors(value, label="probe") == []
    assert TOOL_MODULE.validate_instance(pointer_schema, "value", label="pointer") == (True, [])
    assert TOOL_MODULE.validate_instance(escaped_pointer_schema, 7, label="escaped_pointer") == (True, [])
    assert TOOL_MODULE.validate_instance(anchor_schema, "value", label="anchor") == (True, [])


def test_internal_pointer_cannot_hide_external_reference_in_data_target() -> None:
    schema_value = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "#/const", "const": {"$ref": EXTERNAL_SCHEMA_URI}}
    errors = TOOL_MODULE.schema_reference_policy_errors(schema_value, label="probe")
    assert any("external_reference_not_permitted" in error for error in errors)


def test_modern_registry_backend_denies_runtime_retrieval(monkeypatch: pytest.MonkeyPatch) -> None:
    if TOOL_MODULE.CLOSED_SCHEMA_REGISTRY is None:
        pytest.skip("modern registry backend unavailable")
    attempts = forbid_external_io(monkeypatch)
    validator = TOOL_MODULE._build_closed_validator({"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": EXTERNAL_SCHEMA_URI})
    with pytest.raises(Exception):
        list(validator.iter_errors({}))
    assert attempts == []


def test_refresolver_fallback_denies_runtime_retrieval(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = forbid_external_io(monkeypatch)
    monkeypatch.setattr(TOOL_MODULE, "CLOSED_SCHEMA_REGISTRY", None)
    validator = TOOL_MODULE._build_closed_validator({"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": EXTERNAL_SCHEMA_URI})
    with pytest.raises(Exception):
        list(validator.iter_errors({}))
    assert attempts == []


def test_optional_registry_import_has_executable_fallback() -> None:
    source = TOOL.read_text(encoding="utf-8")
    assert "except ImportError:" in source
    assert "ReferencingRegistry = None" in source
    assert "NoSuchResource = None" in source
    original_registry = TOOL_MODULE.CLOSED_SCHEMA_REGISTRY
    try:
        TOOL_MODULE.CLOSED_SCHEMA_REGISTRY = None
        validator = TOOL_MODULE._build_closed_validator({"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "string"})
        assert validator.is_valid("value") and not validator.is_valid(1)
    finally:
        TOOL_MODULE.CLOSED_SCHEMA_REGISTRY = original_registry


# Canonical reviewed schema identity.

def test_byte_identical_alternate_schema_paths_are_not_canonical(tmp_path: Path) -> None:
    schema_copy = tmp_path / "expectation.schema.json"
    subject_copy = tmp_path / "subject.schema.json"
    schema_copy.write_bytes(EXPECTATION_SCHEMA.read_bytes())
    subject_copy.write_bytes(SUBJECT_INPUT_SCHEMA.read_bytes())
    result = run_tool(schema_path=schema_copy, subject_input_schema_path=subject_copy)
    assert result.returncode == 0
    boundary = parse_json_text(result.stdout)["verification_boundary"]
    assert boundary["supplied_contract_semantics_verified"] is True
    assert boundary["canonical_expectation_schema_path_verified"] is False
    assert boundary["canonical_expectation_schema_git_blob_verified"] is True
    assert boundary["canonical_subject_input_schema_path_verified"] is False
    assert boundary["canonical_subject_input_schema_git_blob_verified"] is True
    assert boundary["canonical_contract_semantics_verified"] is False
    assert boundary["contract_semantics_verified"] is False


@pytest.mark.parametrize("schema_key", ["schema", "subject_schema"])
def test_dirty_canonical_schema_cannot_claim_canonical_contract(tmp_path: Path, schema_key: str) -> None:
    paths = copy_contract_repository(tmp_path)
    dirty = load_json(paths[schema_key])
    dirty["title"] = str(dirty.get("title", "schema")) + " — dirty regression"
    write_json(paths[schema_key], dirty)
    result = run_tool(
        tool=paths["tool"],
        schema_path=paths["schema"],
        expectation_path=paths["expectation"],
        subject_input_schema_path=paths["subject_schema"],
        repository_root=paths["root"],
    )
    assert result.returncode == 0
    diagnostic = parse_json_text(result.stdout)
    boundary = diagnostic["verification_boundary"]
    assert diagnostic["ok"] is True
    assert boundary["supplied_contract_semantics_verified"] is True
    assert boundary["canonical_expectation_schema_path_verified"] is True
    assert boundary["canonical_subject_input_schema_path_verified"] is True
    if schema_key == "schema":
        assert boundary["canonical_expectation_schema_git_blob_verified"] is False
        assert boundary["canonical_subject_input_schema_git_blob_verified"] is True
    else:
        assert boundary["canonical_expectation_schema_git_blob_verified"] is True
        assert boundary["canonical_subject_input_schema_git_blob_verified"] is False
    assert boundary["canonical_contract_semantics_verified"] is False
    assert boundary["contract_semantics_verified"] is False


# Independent schema states and downstream witness.

def test_non_object_subject_schema_preserves_expectation_schema_state(tmp_path: Path) -> None:
    path = tmp_path / "subject-schema.json"
    path.write_text("[]\n", encoding="utf-8")
    result = run_tool(subject_input_schema_path=path)
    assert result.returncode == 2 and result.stderr == ""
    diagnostic = parse_json_text(result.stdout)
    assert diagnostic["expectation_schema_valid"] is True
    assert diagnostic["subject_input_schema_valid"] is False
    assert any("subject_input_schema_not_object" in error for error in diagnostic["errors"])


def test_non_object_expectation_schema_preserves_subject_schema_state(tmp_path: Path) -> None:
    path = tmp_path / "expectation-schema.json"
    path.write_text("[]\n", encoding="utf-8")
    result = run_tool(schema_path=path)
    assert result.returncode == 2 and result.stderr == ""
    diagnostic = parse_json_text(result.stdout)
    assert diagnostic["expectation_schema_valid"] is False
    assert diagnostic["subject_input_schema_valid"] is True
    assert any("expectation_schema_not_object" in error for error in diagnostic["errors"])


def test_missing_subject_schema_preserves_expectation_schema_state(tmp_path: Path) -> None:
    result = run_tool(subject_input_schema_path=tmp_path / "missing-subject-schema.json")
    assert result.returncode == 2 and result.stderr == ""
    diagnostic = parse_json_text(result.stdout)
    assert diagnostic["expectation_schema_valid"] is True
    assert diagnostic["subject_input_schema_valid"] is False


def test_impossible_downstream_observed_branch_fails_separately(tmp_path: Path) -> None:
    subject_schema = load_json(SUBJECT_INPUT_SCHEMA)
    subject_schema.setdefault("allOf", []).append({"not": {"properties": {"record_status": {"const": "observed"}}, "required": ["record_status"]}})
    path = tmp_path / "impossible-observed.schema.json"
    write_json(path, subject_schema)
    result = run_tool(subject_input_schema_path=path)
    assert result.returncode == 1 and result.stderr == ""
    diagnostic = parse_json_text(result.stdout)
    assert diagnostic["expectation_schema_valid"] is True
    assert diagnostic["expectation_instance_valid"] is True
    assert diagnostic["subject_input_schema_valid"] is True
    assert diagnostic["subject_input_schema_reference_policy_valid"] is True
    assert diagnostic["subject_input_observed_branch_valid"] is False
    assert diagnostic["ok"] is False


def test_complete_downstream_witness_contains_required_packet_surfaces() -> None:
    value = expectation()
    witness = TOOL_MODULE._subject_input_observed_witness(value, packet_contract=value["packet_contract"], profile=value["packet_producer_profile"])
    assert set(witness) == {
        "analysis_boundary", "artifacts", "authority_boundary", "authority_sources",
        "carrier", "content_boundary", "coverage", "errors", "ok", "packet_identity",
        "packet_type", "producer", "record_status", "role_bindings", "schema_version", "subject",
    }
    valid, errors = TOOL_MODULE.validate_instance(load_json(SUBJECT_INPUT_SCHEMA), witness, label="subject_input_observed_branch_witness")
    assert valid is True and errors == []


# Observed expectation branch.

def test_valid_observed_expectation_passes(tmp_path: Path) -> None:
    path = tmp_path / "observed-expectation.json"
    write_json(path, observed_expectation())
    result = run_tool(expectation_path=path)
    assert result.returncode == 0 and result.stderr == ""
    diagnostic = parse_json_text(result.stdout)
    assert diagnostic["ok"] is True
    assert diagnostic["record_status"] == "observed"
    assert diagnostic["derived"]["record_status"] == "observed"
    assert diagnostic["checks"]["record_status_branch_ok"] is True
    assert diagnostic["checks"]["observed_producer_bindings_ok"] is True
    assert diagnostic["subject_input_observed_branch_valid"] is True


@pytest.mark.parametrize(
    ("path_parts", "replacement"),
    [
        (("expectation_producer", "producer_source"), "tools/other-builder.py"),
        (("expectation_producer", "producer_source_revision"), "f" * 40),
        (("expectation_producer", "producer_source_sha256"), "f" * 64),
        (("expectation_producer", "producer_version"), "9.9.9"),
        (("expectation_producer", "producer_run_key"), "GITHUB_RUN_ID=9002|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI"),
        (("carrier", "producer", "producer_source_revision"), "f" * 40),
        (("carrier", "producer", "producer_run_key"), "GITHUB_RUN_ID=9002|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI"),
    ],
)
def test_observed_producer_binding_mismatches_fail_closed(tmp_path: Path, path_parts: tuple[str, ...], replacement: str) -> None:
    value = observed_expectation()
    cursor: dict[str, Any] = value
    for part in path_parts[:-1]:
        nested = cursor[part]
        assert isinstance(nested, dict)
        cursor = nested
    cursor[path_parts[-1]] = replacement
    path = tmp_path / "observed-mismatch.json"
    write_json(path, value)
    diagnostic = assert_validation_failure(run_tool(expectation_path=path), "observed_producer_bindings_ok")
    assert diagnostic["expectation_schema_valid"] is True
    assert diagnostic["expectation_instance_valid"] is True
    assert diagnostic["checks"]["observed_producer_bindings_ok"] is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
