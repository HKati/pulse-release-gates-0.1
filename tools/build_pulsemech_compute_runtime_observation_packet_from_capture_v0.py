#!/usr/bin/env python3
"""Build a bounded historical runtime packet from the exact accepted #6066 input.

Run with Python -I on Linux. This is an offline, non-authoritative producer,
not live instrumentation and not a connected runtime proof. Subject records
are platform metadata, not evidence of executed command bytes or input/output
consumption. Empty call/usage collections mean unobserved, not proven absent.

The canonical construction record is a separately preserved input. Its times
and collector identity describe the construction being replayed, not a fresh
clock measurement by this invocation. The producer checks content identities
and temporal consistency, not independent authentication of that declaration.
Required record fields are enumerated in CONSTRUCTION_FIELDS below. Supply
its external SHA-256 with --construction-sha256; packet bytes never use the
current time, filesystem paths, random values or ambient environment values.

Source preparation and review output belong outside the repository. Source
and carrier bytes are never modified. Existing outputs are never replaced.
"""
from __future__ import annotations

import sys

if __name__ == "__main__" and not (
    sys.flags.isolated == 1
    and sys.flags.ignore_environment == 1
    and sys.flags.no_user_site == 1
    and getattr(sys.flags, "safe_path", False)
):
    sys.stderr.write(
        '{"authority_effect":"none","error_code":"isolated_python_required",'
        '"ok":false,"tool":"build_pulsemech_compute_runtime_observation_packet_from_capture_v0"}\n'
    )
    raise SystemExit(2)

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import tempfile
import types
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

TOOL_NAME = "build_pulsemech_compute_runtime_observation_packet_from_capture_v0"
TOOL_VERSION = "0.1.0"
SOURCE_PATH = f"tools/{TOOL_NAME}.py"
# Preserve the invoked path without resolving symlinks into an accepted name.
EXECUTED_SOURCE_PATH = Path(__file__).absolute()
ROOT = EXECUTED_SOURCE_PATH.parents[1]
MODE = "post_run_platform_export"
RUNTIME_VALIDATOR = "tools/check_pulsemech_compute_runtime_observation_packet_v0.py"
CAPTURE_VALIDATOR = "tools/check_pulsemech_compute_post_run_producer_input_capture_v0.py"
CONTEXT_VALIDATOR = "tools/check_pulsemech_compute_subject_input_packet_v0.py"
RUNTIME_SCHEMA = "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json"
CONTEXT_SCHEMA = "schemas/pulsemech_compute_subject_input_packet_v0.schema.json"
CONTEXT_PATH = "examples/compute/pulsemech_compute_subject_input_packet_6066_observed_v0.json"
CARRIER_PATH = "PULSE_CI_6066_release_grade_artifact_preservation_v0.zip"
CAPTURE_ROOT = "preservation/pulse_ci_6066/post_run_producer_input_capture_v0"
MANIFEST_NAME = "pulsemech_compute_post_run_producer_input_capture_manifest_6066_v0.json"
MANIFEST_SHA256 = "4642546646fc7c78f8b65bce40c3db72fb6847c4e3d454db97b164f1fc14f238"
CONTEXT_SHA256 = "b457383356d330ae40843a47f9adb83c4e7d7f14447218f951ca71e4ee287467"
CARRIER_SHA256 = "7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966"
HISTORICAL_COMMIT = "46b639706e23f80fe296a8893be18e2b5ab21f7e"
SUBJECT_KEY = "GITHUB_RUN_ID=29249887581|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI"
# Fixed unchanged input validators and schemas: never execute an unchecked
# replacement helper. The matching runtime-validator update is pinned here
# as well as to the separately identified construction source revision.
FIXED_SOURCES = {
    RUNTIME_VALIDATOR: (49528, "edc8f795043f656ffa8599dfae9555f38970790f1096cf080e9049f218d512d9"),
    CAPTURE_VALIDATOR: (110820, "ae5f608cb773ccf541ad1f703713773c59750b4f3997899b8c00f0a2b0d835ca"),
    CONTEXT_VALIDATOR: (92218, "a9690c8cdba3b4192eea0033b627d3b99b507019f4afbfc0bdb003c531f35383"),
    RUNTIME_SCHEMA: (70467, "824991a9f5c21ca9bd9fd7d1fc5c5813af3ff0ef9714c8506d2c3e6a5f9fa0cc"),
    CONTEXT_SCHEMA: (33513, "81c274aaee7cd2aee015eda490cc82bd19f7556db35e2c3dc9995fbdb8d96e19"),
}
CAPTURE_SIZES = {
    MANIFEST_NAME: 17905,
    "metadata/run_attempt_exchange_v0.json": 2886,
    "metadata/jobs_page_0001_exchange_v0.json": 3036,
    "raw/run_attempt_response.json": 15097,
    "raw/jobs_page_0001_response.json": 38004,
}
CONSTRUCTION_FIELDS = frozenset({
    "record_type", "collection_mode", "subject_run_key",
    "producer_source_revision", "producer_source_sha256", "runtime_validator_sha256",
    "capture_manifest_sha256", "subject_context_sha256", "carrier_sha256",
    "collector_run_key", "collector_execution_id", "collector_workflow_name",
    "collector_job_name", "collector_attempt", "capture_started_utc",
    "capture_completed_utc", "packet_created_utc",
})
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_CONSTRUCTION_BYTES = 16384
FORBIDDEN_OUTPUT_NAMES = frozenset({
    "status.json", "release_decision_v0.json", "release_authority_v0.json",
    "pulse_gate_policy_v0.yml", "pulse_gate_registry_v0.yml",
    "pulsemech_compute_subject_input_packet_v0.json",
})
UTC_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{1,6})?Z"
)


class ProducerError(RuntimeError):
    def __init__(self, code: str, stage: str = "producer") -> None:
        super().__init__(code)
        self.code = code
        self.stage = stage


def require(condition: bool, code: str, stage: str = "producer") -> None:
    if not condition:
        raise ProducerError(code, stage)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key", "json")
        result[key] = value
    return result


def _invalid_number(_: str) -> None:
    raise ProducerError("non_finite_or_fractional_construction_number", "json")


def _normalized(value: Any) -> bool:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value) == value
    if isinstance(value, dict):
        return all(_normalized(k) and _normalized(v) for k, v in value.items())
    if isinstance(value, list):
        return all(_normalized(v) for v in value)
    return value is None or type(value) in (int, bool)


def parse_object(data: bytes, *, canonical: bool = False) -> dict[str, Any]:
    require(not data.startswith(b"\xef\xbb\xbf"), "bom_rejected", "json")
    try:
        obj = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                         parse_constant=_invalid_number, parse_float=_invalid_number)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ProducerError("invalid_json", "json") from exc
    require(isinstance(obj, dict), "json_object_required", "json")
    require(_normalized(obj), "noncanonical_json_value", "json")
    if canonical:
        require(canonical_bytes(obj) == data, "noncanonical_construction_record", "json")
    return obj


def utc(value: str) -> datetime:
    require(isinstance(value, str) and UTC_RE.fullmatch(value) is not None,
            "invalid_utc_timestamp", "time")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError as exc:
        raise ProducerError("invalid_calendar_timestamp", "time") from exc


def absolute(path: Path) -> Path:
    require(".." not in path.parts, "parent_traversal_rejected", "path")
    return Path(os.path.abspath(path))


def _open_directory(path: Path) -> int:
    """Hold the actual hierarchy, never resolve a symlink before checking it."""
    path = absolute(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(path.anchor, flags)
    try:
        for name in path.parts[1:]:
            child = os.open(name, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _fingerprint(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, stat.S_IMODE(info.st_mode), info.st_nlink)


@dataclass(frozen=True)
class InputFile:
    path: Path
    data: bytes
    fingerprint: tuple[int, ...]


def read_input(path: Path, *, maximum: int, exact_size: int | None = None) -> InputFile:
    path = absolute(path)
    directory = _open_directory(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                     dir_fd=directory)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                    "regular_unlinked_input_required", "input")
            if exact_size is not None:
                require(before.st_size == exact_size, "input_size_mismatch", "input")
            require(0 < before.st_size <= maximum, "input_size_out_of_range", "input")
            chunks: list[bytes] = []
            remaining = before.st_size + 1
            while remaining:
                chunk = os.read(fd, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            require(len(data) == before.st_size and _fingerprint(os.fstat(fd)) ==
                    _fingerprint(before), "input_changed_during_read", "input")
            named = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
            require(_fingerprint(named) == _fingerprint(before),
                    "input_replaced_during_read", "input")
            return InputFile(path, data, _fingerprint(before))
        finally:
            os.close(fd)
    finally:
        os.close(directory)


def exact_input(path: Path, size: int, digest: str) -> InputFile:
    result = read_input(path, maximum=size, exact_size=size)
    require(sha256(result.data) == digest, "input_digest_mismatch", "input")
    return result


def capture_inventory(root: Path) -> dict[str, tuple[int, int]]:
    directories = {"": {MANIFEST_NAME, "raw", "metadata"},
                   "raw": {"run_attempt_response.json", "jobs_page_0001_response.json"},
                   "metadata": {"run_attempt_exchange_v0.json", "jobs_page_0001_exchange_v0.json"}}
    identities: dict[str, tuple[int, int]] = {}
    for relative, expected in directories.items():
        fd = _open_directory(root / relative)
        try:
            require(set(os.listdir(fd)) == expected, "capture_inventory_mismatch", "capture")
            info = os.fstat(fd)
            identities[relative] = (info.st_dev, info.st_ino)
        finally:
            os.close(fd)
    return identities


def load_module(path: Path, data: bytes, name: str) -> Any:
    # Execute the exact checked byte string, not a subsequent loader reread.
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None, "module_spec_unavailable", "source")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__spec__ = spec
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def construction(data: bytes, digest: str) -> dict[str, Any]:
    require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
            "construction_digest_required", "construction")
    require(sha256(data) == digest, "construction_digest_mismatch", "construction")
    record = parse_object(data, canonical=True)
    require(set(record) == CONSTRUCTION_FIELDS, "construction_field_set_mismatch", "construction")
    constants = {
        "record_type": "pulsemech_compute_runtime_packet_construction_v0",
        "collection_mode": MODE, "subject_run_key": SUBJECT_KEY,
        "capture_manifest_sha256": MANIFEST_SHA256,
        "subject_context_sha256": CONTEXT_SHA256, "carrier_sha256": CARRIER_SHA256,
    }
    require(all(record[k] == v for k, v in constants.items()),
            "construction_input_binding_mismatch", "construction")
    for key in ("producer_source_sha256", "runtime_validator_sha256"):
        require(isinstance(record[key], str) and re.fullmatch(r"[0-9a-f]{64}", record[key])
                is not None, "construction_source_digest_invalid", "construction")
    revision = record["producer_source_revision"]
    require(isinstance(revision, str) and re.fullmatch(r"[0-9a-f]{40}", revision) is not None,
            "construction_source_revision_invalid", "construction")
    for key in ("collector_run_key", "collector_workflow_name", "collector_job_name"):
        value = record[key]
        require(isinstance(value, str) and 0 < len(value) <= 256 and
                all(32 <= ord(ch) < 127 for ch in value),
                "construction_collector_identity_invalid", "construction")
    require(record["collector_run_key"] != SUBJECT_KEY,
            "collector_must_be_separate_from_subject", "construction")
    identifier = record["collector_execution_id"]
    require(isinstance(identifier, str) and re.fullmatch(
        r"execution:[A-Za-z0-9][A-Za-z0-9._:/-]{0,200}", identifier) is not None,
        "collector_execution_id_invalid", "construction")
    attempt = record["collector_attempt"]
    require(type(attempt) is int and attempt >= 1, "collector_attempt_invalid", "construction")
    started, completed, created = (utc(record[k]) for k in (
        "capture_started_utc", "capture_completed_utc", "packet_created_utc"))
    require(started <= completed <= created, "construction_time_order_invalid", "time")
    return record


def _unknown_source() -> dict[str, Any]:
    return {"source_kind": "unknown", "identity_status": "unknown",
            **{k: None for k in ("source_path_or_uri", "source_revision", "source_sha256",
                                "action_repository", "action_ref", "action_commit_sha",
                                "container_image_digest")}}


def _source(path: str, revision: str, digest: str, *, status: str) -> dict[str, Any]:
    value = _unknown_source()
    value.update(source_kind="repository_file", identity_status=status,
                 source_path_or_uri=path, source_revision=revision, source_sha256=digest)
    return value


def _environment() -> dict[str, Any]:
    return {"environment_kind": "unknown", "identity_status": "unknown",
            "raw_environment_included": False,
            **{k: None for k in ("os_name", "os_version", "architecture", "runtime_name",
                                "runtime_version", "image_identity", "image_digest", "environment_sha256")}}


def timing(started: str | None, completed: str | None, source: str) -> dict[str, Any]:
    # Keep original timestamp strings. No runtime/resource measurement is made.
    duration: int | float | None = None
    for value in (started, completed):
        if value is not None:
            utc(value)
    if started is not None and completed is not None:
        delta = utc(completed) - utc(started)
        micros = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
        require(micros >= 0, "execution_time_order_invalid", "time")
        duration = micros // 1000 if micros % 1000 == 0 else micros / 1000
    observed = started is not None or completed is not None
    return {"timing_status": "complete" if duration is not None else "partial" if observed else "unknown",
            "started_utc": started, "completed_utc": completed, "duration_ms": duration,
            "timestamp_source": source if observed else "unknown",
            "duration_source": "derived_from_timestamps" if duration is not None else "unknown"}


def result_from_platform(row: dict[str, Any]) -> dict[str, Any]:
    lifecycle = row["status"]
    outcome = row["conclusion"]
    require(lifecycle in {"queued", "in_progress", "completed", "skipped", "cancelled"},
            "platform_lifecycle_not_representable", "mapping")
    require(outcome in {"success", "failure", "cancelled", "skipped", "neutral", "timed_out"},
            "platform_outcome_not_representable", "mapping")
    # status and conclusion are copied verbatim. An exit code was not observed.
    return {"result_status": "partial", "lifecycle_status": lifecycle,
            "outcome": outcome, "exit_code": None}


def _execution(subject: dict[str, Any], job: dict[str, Any],
               step: dict[str, Any] | None, workflow_digest: str) -> dict[str, Any]:
    base = f"execution:github-run-{subject['workflow_run_id']}-attempt-{subject['workflow_run_attempt']}-job-{job['id']}"
    row = job if step is None else step
    identifier = base if step is None else f"{base}-step-{step['number']:06d}"
    return {
        "execution_id": identifier, "execution_scope": "subject",
        "execution_kind": "workflow_job" if step is None else "workflow_step",
        "parent_execution_id": None if step is None else base,
        "workflow_name": subject["workflow_name"], "job_name": job["name"],
        "job_id": job["id"], "job_attempt": job["run_attempt"],
        "step_name": None if step is None else step["name"],
        "step_number": None if step is None else step["number"],
        "source_identity": (_source(".github/workflows/pulse_ci.yml", subject["source_commit"],
                                    workflow_digest, status="partial") if step is None else _unknown_source()),
        "command_identity": {"command_kind": "unknown", "display_name": row["name"],
                             "command_sha256": None, "arguments_sha256": None, "raw_command_included": False},
        "execution_environment": _environment(),
        "run_binding": {"subject_run_key": SUBJECT_KEY, "execution_run_key": SUBJECT_KEY,
                        "binding_mode": "current_subject_run", "binding_complete": True},
        "timing": timing(row.get("started_at"), row.get("completed_at"), "platform_reported"),
        "result": result_from_platform(row), "declared_role": "unknown",
        # This packet admits no historical mutation authority. This is not a
        # claim that the historical job lacked permissions or had no effects.
        "permitted_mutation_authority": "none",
        "input_state_ids": [], "output_state_ids": [], "external_call_ids": [],
        "model_inference_ids": [], "resource_measurement_ids": [], "capture_status": "partial",
    }


def construct_packet(*, record: dict[str, Any], record_bytes: bytes,
                     context: dict[str, Any], capture: dict[str, bytes],
                     sources: dict[str, tuple[str, str, bytes]],
                     dependencies: dict[str, bytes], carrier_bytes: bytes,
                     runtime: Any) -> dict[str, Any]:
    """Pure deterministic projection, invoked only after input validation."""
    raw = parse_object(capture["raw/run_attempt_response.json"])
    manifest = parse_object(capture[MANIFEST_NAME])
    subject = {key: context["subject"][key] for key in (
        "repository", "workflow_name", "workflow_run_id", "workflow_run_number",
        "workflow_run_attempt", "subject_run_key", "source_commit", "source_ref",
        "event_name", "release_candidate_id", "run_mode", "active_policy_sets")}
    aliases = {"workflow_name": "name", "workflow_run_id": "id", "workflow_run_number": "run_number",
               "workflow_run_attempt": "run_attempt", "source_commit": "head_sha", "event_name": "event"}
    require(all(subject[k] == raw[v] == manifest["subject"][k] for k, v in aliases.items())
            and subject["repository"] == raw["repository"]["full_name"]
            and subject["source_ref"] == manifest["subject"]["source_ref"]
            and subject["subject_run_key"] == manifest["subject"]["subject_run_key"],
            "historical_context_subject_mismatch", "subject")
    jobs = parse_object(capture["raw/jobs_page_0001_response.json"])["jobs"]
    executions = []
    for job in jobs:
        executions.append(_execution(subject, job, None, context["authority_sources"]["workflow"]["sha256"]))
        for step in job.get("steps", []):
            executions.append(_execution(subject, job, step, context["authority_sources"]["workflow"]["sha256"]))
    require(len(jobs) == 8 and len(executions) == 179, "historical_inventory_mismatch", "mapping")
    exchanges = [manifest["run_attempt_exchange"]["record"],
                 *(item["record"] for item in manifest["jobs_page_exchanges"])]
    acquisition_start = min(utc(e["response"]["timing"]["capture_started_utc"]) for e in exchanges)
    acquisition_end = max(utc(e["response"]["timing"]["response_received_utc"]) for e in exchanges)
    require(utc(raw["updated_at"]) <= acquisition_start <= acquisition_end <= utc(record["capture_started_utc"]),
            "subject_acquisition_construction_order_invalid", "time")
    for row in executions:
        for field in ("started_utc", "completed_utc"):
            value = row["timing"][field]
            require(value is None or utc(value) <= acquisition_start,
                    "historical_execution_after_acquisition", "time")
    collector_id = record["collector_execution_id"]
    require(collector_id not in {row["execution_id"] for row in executions},
            "collector_identifier_collision", "mapping")
    states: list[dict[str, Any]] = []

    def state(name: str, kind: str, path: str, data: bytes, *, authority: bool = False,
              media: str = "application/json") -> None:
        states.append({
            "state_id": f"state:{name}", "state_type": kind, "path_or_uri": path,
            "content_status": "exact_digest", "sha256": sha256(data), "size_bytes": len(data),
            "media_type": media, "schema_identity": None, "producer_execution_id": None,
            "observer_execution_id": collector_id, "subject_run_key": SUBJECT_KEY,
            "release_candidate_id": subject["release_candidate_id"], "authority_bearing": authority,
            "mutation_class": "none", "observed_at_utc": record["capture_completed_utc"],
            "secret_material_included": False,
        })

    for relative, data in sorted(capture.items()):
        state("capture/" + relative, "manifest" if relative == MANIFEST_NAME else "preservation_record",
              f"{CAPTURE_ROOT}/{relative}", data)
    state("subject-context", "preservation_record", CONTEXT_PATH, canonical_bytes(context))
    state("subject-carrier", "package", CARRIER_PATH, carrier_bytes, media="application/zip")
    state("construction-record", "preservation_record", f"sha256:{sha256(record_bytes)}", record_bytes)
    authority_inputs: dict[str, Any] = {}
    kinds = {"workflow": "workflow_source", "policy": "policy", "gate_registry": "gate_registry"}
    for name, (path, revision, data) in sorted(sources.items()):
        is_authority = name in kinds
        state("source/" + name, kinds.get(name, "other"), path if is_authority else f"git:{revision}:{path}",
              data, authority=is_authority, media="text/plain")
        if is_authority:
            authority_inputs[name] = {"path": path, "role": name, "source_commit": revision,
                                      "sha256": sha256(data)}
    for path, data in sorted(dependencies.items()):
        state("implementation/" + path, "other", f"git:{record['producer_source_revision']}:{path}",
              data, media="text/plain")
    collector = {
        "execution_id": collector_id, "execution_scope": "observation_collector",
        "execution_kind": "observer_execution", "parent_execution_id": None,
        "workflow_name": record["collector_workflow_name"], "job_name": record["collector_job_name"],
        "job_id": None, "job_attempt": record["collector_attempt"], "step_name": None, "step_number": None,
        "source_identity": _source(SOURCE_PATH, record["producer_source_revision"],
                                   record["producer_source_sha256"], status="exact"),
        "command_identity": {"command_kind": "python_script", "display_name": TOOL_NAME,
                             "command_sha256": None, "arguments_sha256": None, "raw_command_included": False},
        "execution_environment": _environment(),
        "run_binding": {"subject_run_key": SUBJECT_KEY, "execution_run_key": record["collector_run_key"],
                        "binding_mode": "post_run_observer", "binding_complete": True},
        "timing": timing(record["capture_started_utc"], record["capture_completed_utc"], "tool_reported"),
        "result": {"result_status": "unknown", "lifecycle_status": "unknown", "outcome": "unknown", "exit_code": None},
        "declared_role": "observer", "permitted_mutation_authority": "advisory_output",
        "input_state_ids": sorted(row["state_id"] for row in states), "output_state_ids": [],
        "external_call_ids": [], "model_inference_ids": [], "resource_measurement_ids": [], "capture_status": "partial",
    }
    executions.append(collector)
    return {
        "schema_version": "pulsemech_compute_runtime_observation_packet_v0",
        "packet_type": "pulsemech_compute_runtime_observation_packet", "record_status": "observed",
        "producer": {"producer_id": TOOL_NAME, "producer_name": "PULSEmech offline historical runtime-packet producer",
                     "producer_version": TOOL_VERSION, "producer_source": SOURCE_PATH,
                     "producer_source_sha256": record["producer_source_sha256"],
                     "ci_workflow_or_job_identity": record["collector_workflow_name"] + " / " + record["collector_job_name"],
                     "collection_mode": MODE, "producer_execution_id": collector_id},
        "packet_identity": {"packet_id": "runtime-observation:post-run-6066-" + sha256(record_bytes),
                            "packet_sequence": 0, "packet_scope": "external_export", "subject_run_key": SUBJECT_KEY,
                            "packet_created_utc": record["packet_created_utc"], "previous_packet_sha256": None,
                            "canonicalization": "json-sort-keys-utf8-newline"},
        "subject": subject,
        "observation_boundary": {"target_analysis_level": "runtime_observed", "subject_run_key": SUBJECT_KEY,
                                 "collector_run_key": record["collector_run_key"], "collector_execution_id": collector_id,
                                 "collector_mode": MODE, "observer_in_subject_totals": False,
                                 "capture_started_utc": record["capture_started_utc"],
                                 "capture_completed_utc": record["capture_completed_utc"], "subject_artifacts_mutated": False},
        "authority_inputs": authority_inputs,
        "timing_basis": {"timestamps_utc": True, "primary_clock_source": "mixed", "timestamp_resolution_ms": 1000,
                         "cross_source_clock_status": "not_verified", "duration_derivation": "derived_from_recorded_timestamps",
                         "duration_values_estimated": False},
        "privacy_boundary": {**{k: False for k in ("raw_environment_included", "secret_values_included", "authorization_headers_included",
                                                  "cookies_included", "request_bodies_included", "response_bodies_included",
                                                  "raw_prompt_text_included", "raw_model_output_included", "redaction_applied")},
                             "redaction_rules_sha256": None},
        "executions": sorted(executions, key=lambda row: row["execution_id"]),
        "state_observations": sorted(states, key=lambda row: row["state_id"]),
        "external_calls": [], "model_inferences": [], "resource_measurements": [],
        "coverage": {"coverage_status": "partial", "expected_job_count": 8, "observed_job_count": 8,
                     "expected_step_count": 171, "observed_step_count": 171, "execution_records": len(executions),
                     "state_records": len(states), "external_call_records": 0, "model_inference_records": 0,
                     "resource_measurement_records": 0, "missing_execution_ids": [],
                     "unobserved_reasons": sorted(["step_not_instrumented", "external_provider_usage_unavailable",
                                                   "model_content_digest_unavailable", "resource_axis_unavailable"]),
                     "resource_axes_observed": [], "resource_axes_unavailable": sorted(runtime.RESOURCE_AXES),
                     "external_call_capture_status": "none", "model_inference_capture_status": "none",
                     "state_digest_capture_status": "complete"},
        "errors": [], "ok": True,
    }


def _unlink_owned(directory: int, name: str, identity: tuple[int, int]) -> None:
    try:
        current = os.stat(name, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        return
    if (current.st_dev, current.st_ino) == identity and stat.S_ISREG(current.st_mode):
        os.unlink(name, dir_fd=directory)


def publish_no_replace(output: Path, payload: bytes, *, repository: Path,
                       recheck: Callable[[], None]) -> None:
    output, repository = absolute(output), absolute(repository)
    require(not output.is_relative_to(repository), "output_inside_repository_forbidden", "output")
    require(output.name not in FORBIDDEN_OUTPUT_NAMES and output.suffix == ".json",
            "authority_or_non_json_output_forbidden", "output")
    directory = _open_directory(output.parent)
    staged: str | None = None
    fd: int | None = None
    identity: tuple[int, int] | None = None
    parent_info = os.fstat(directory)
    try:
        try:
            os.stat(output.name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ProducerError("output_already_exists", "output")
        staged = ".pulse-runtime-" + os.urandom(16).hex() + ".tmp"
        fd = os.open(staged, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=directory)
        info = os.fstat(fd)
        identity = (info.st_dev, info.st_ino)
        view = memoryview(payload)
        while view:
            count = os.write(fd, view)
            require(count > 0, "output_short_write", "output")
            view = view[count:]
        os.fsync(fd)
        recheck()
        os.link(staged, output.name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        named = os.stat(output.name, dir_fd=directory, follow_symlinks=False)
        require((named.st_dev, named.st_ino) == identity and stat.S_ISREG(named.st_mode),
                "output_replaced_during_publication", "output")
        os.lseek(fd, 0, os.SEEK_SET)
        chunks = []
        remaining = len(payload) + 1
        while remaining:
            part = os.read(fd, min(65536, remaining))
            if not part:
                break
            chunks.append(part)
            remaining -= len(part)
        require(b"".join(chunks) == payload, "published_output_bytes_changed", "output")
        recheck()
        current_parent = _open_directory(output.parent)
        try:
            current = os.fstat(current_parent)
            require((current.st_dev, current.st_ino) == (parent_info.st_dev, parent_info.st_ino),
                    "output_parent_replaced", "output")
        finally:
            os.close(current_parent)
        final = os.stat(output.name, dir_fd=directory, follow_symlinks=False)
        require((final.st_dev, final.st_ino) == identity and
                final.st_size == len(payload) and stat.S_ISREG(final.st_mode),
                "output_replaced_after_recheck", "output")
        os.lseek(fd, 0, os.SEEK_SET)
        verified = bytearray()
        while len(verified) <= len(payload):
            chunk = os.read(fd, min(65536, len(payload) + 1 - len(verified)))
            if not chunk:
                break
            verified.extend(chunk)
        require(bytes(verified) == payload, "output_changed_after_recheck", "output")
        _unlink_owned(directory, staged, identity)
        staged = None
        os.fsync(directory)
    except BaseException:
        if identity is not None:
            # Link may have succeeded before an interruption was raised. Only
            # our inode may be removed, whether or not link() returned normally.
            _unlink_owned(directory, output.name, identity)
            if staged is not None:
                _unlink_owned(directory, staged, identity)
        raise
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory)


def build(*, repository_root: Path, capture_root: Path, subject_context: Path,
          carrier: Path, construction_record: Path, construction_sha256: str,
          output: Path) -> dict[str, Any]:
    require(sys.platform.startswith("linux") and os.name == "posix",
            "linux_runtime_required", "runtime")
    repository = absolute(repository_root)
    require(repository == absolute(ROOT), "executed_source_repository_mismatch", "source")
    executed_path = absolute(EXECUTED_SOURCE_PATH)
    require(executed_path == repository / SOURCE_PATH,
            "executed_source_path_mismatch", "source")
    # Snapshot the invoked file itself before loading any helper. The same
    # bytes must match the construction digest and exact commit:path below,
    # and remain protected through both publication rechecks. A canonical
    # neighbour cannot supply provenance for a renamed or modified copy.
    self_file = read_input(executed_path, maximum=MAX_SOURCE_BYTES)
    files: list[InputFile] = [self_file]
    fixed = {path: exact_input(repository / path, size, digest)
             for path, (size, digest) in FIXED_SOURCES.items()}
    files.extend(fixed.values())
    cap = load_module(fixed[CAPTURE_VALIDATOR].path, fixed[CAPTURE_VALIDATOR].data, "_pulse_step4b_capture_validator")
    cap._install_network_audit_guard()
    record_file = read_input(construction_record, maximum=MAX_CONSTRUCTION_BYTES)
    files.append(record_file)
    record = construction(record_file.data, construction_sha256)
    runtime_file = fixed[RUNTIME_VALIDATOR]
    require(sha256(self_file.data) == record["producer_source_sha256"], "producer_source_digest_mismatch", "source")
    require(sha256(runtime_file.data) == record["runtime_validator_sha256"], "runtime_validator_digest_mismatch", "source")
    dependency_bytes = {path: item.data for path, item in fixed.items()}
    dependency_bytes.update({SOURCE_PATH: self_file.data, RUNTIME_VALIDATOR: runtime_file.data})
    context_file = exact_input(subject_context, 45914, CONTEXT_SHA256)
    carrier_file = exact_input(carrier, 44660, CARRIER_SHA256)
    files.extend((context_file, carrier_file))
    context = parse_object(context_file.data, canonical=True)
    capture_directories = capture_inventory(capture_root)
    capture_files = {path: read_input(capture_root / path, maximum=size, exact_size=size)
                     for path, size in CAPTURE_SIZES.items()}
    files.extend(capture_files.values())
    require(sha256(capture_files[MANIFEST_NAME].data) == MANIFEST_SHA256,
            "capture_manifest_digest_mismatch", "capture")
    capture = {path: item.data for path, item in capture_files.items()}
    repo_fd = cap._open_repository_root(repository)
    bound_sources: dict[str, tuple[str, str, bytes]] = {}
    git_bindings: dict[tuple[str, str], bytes] = {}
    verified_revisions: set[str] = set()

    def git_source(revision: str, path: str) -> bytes:
        if revision not in verified_revisions:
            code, kind = cap._run_git(repo_fd, ["cat-file", "-t", revision],
                                      maximum_output=64, allow_failure=True)
            require(code == 0, "packet_source_committed_bytes_unavailable", "source")
            require(kind.strip() == b"commit", "packet_source_revision_not_commit", "source")
            verified_revisions.add(revision)
        item = cap._load_git_object(repo_fd, role="packet_source", path=path, revision=revision,
                                    maximum=MAX_SOURCE_BYTES, allow_example_head_fallback=False)
        git_bindings[(revision, path)] = item.exact_bytes
        return item.exact_bytes

    def recheck() -> None:
        require(capture_inventory(capture_root) == capture_directories,
                "capture_directory_replaced", "recheck")
        for item in files:
            now = read_input(item.path, maximum=len(item.data), exact_size=len(item.data))
            require(now.data == item.data and now.fingerprint == item.fingerprint,
                    "protected_input_changed", "recheck")
        for (revision, path), expected in list(git_bindings.items()):
            require(git_source(revision, path) == expected, "bound_git_source_changed", "recheck")

    try:
        for path, data in dependency_bytes.items():
            require(git_source(record["producer_source_revision"], path) == data,
                    "executed_source_not_committed_identity", "source")
        # Resolve historical source/provenance objects before the context checker
        # runs. Missing history cannot trigger an implicit substitute or fetch.
        for name, row in context["authority_sources"].items():
            rows = list(enumerate(row)) if name == "additional_sources" else [(name, row)]
            for label, source in rows:
                revision, path = source["source_revision"], source["path_or_uri"]
                require(revision == HISTORICAL_COMMIT, "context_source_revision_mismatch", "source")
                data = git_source(revision, path)
                require(len(data) == source["size_bytes"] and sha256(data) == source["sha256"],
                        "historical_source_identity_mismatch", "source")
                key = f"additional-{label}" if name == "additional_sources" else name
                bound_sources[key] = (path, revision, data)
        context_producer = context["producer"]
        data = git_source(context_producer["producer_source_revision"], context_producer["producer_source"])
        require(sha256(data) == context_producer["producer_source_sha256"],
                "context_producer_source_mismatch", "source")
        bound_sources["context-producer"] = (context_producer["producer_source"],
                                            context_producer["producer_source_revision"], data)
        manifest = parse_object(capture[MANIFEST_NAME])
        for label, row in manifest["contract_bindings"].items():
            data = git_source(row["source_revision"], row["path"])
            require(sha256(data) == row["sha256"] and len(data) == row["size_bytes"],
                    "capture_contract_source_mismatch", "source")
            bound_sources["capture-" + label] = (row["path"], row["source_revision"], data)
        for key, prefix, path_field, revision_field, digest_field in (
            ("capture_implementation", "acquisition-producer", "producer_source", "producer_source_revision", "producer_source_sha256"),
            ("capture_workflow_execution", "acquisition-workflow", "workflow_path", "workflow_source_revision", "workflow_source_sha256"),
        ):
            row = manifest["provenance"][key]
            data = git_source(row[revision_field], row[path_field])
            require(sha256(data) == row[digest_field], "acquisition_source_mismatch", "source")
            bound_sources[prefix] = (row[path_field], row[revision_field], data)
        subject_checker = load_module(fixed[CONTEXT_VALIDATOR].path, fixed[CONTEXT_VALIDATOR].data,
                                      "_pulse_step4b_subject_validator")
        runtime = load_module(runtime_file.path, runtime_file.data, "_pulse_step4b_runtime_validator")
        # A private, exact-byte restoration meets the unchanged capture checker's
        # 0700/0600 contract without chmodding the repository's tracked originals.
        with tempfile.TemporaryDirectory(prefix="pulse-runtime-input-") as temporary:
            private = Path(temporary)
            for directory in (private / "capture", private / "capture/raw", private / "capture/metadata"):
                directory.mkdir(mode=0o700)
            for relative, data in capture.items():
                destination = private / "capture" / relative
                destination.write_bytes(data)
                destination.chmod(0o600)
            cap_result = cap.validate_capture(repository_root=repository, capture_root=private / "capture")
            require(cap_result.record_status == "observed" and cap_result.manifest_sha256 == MANIFEST_SHA256
                    and (cap_result.page_count, cap_result.job_count, cap_result.step_record_count) == (1, 8, 171),
                    "capture_validator_result_mismatch", "capture")
            private_context, private_carrier = private / "context.json", private / "carrier.zip"
            private_context.write_bytes(context_file.data)
            private_carrier.write_bytes(carrier_file.data)
            context_diagnostic, code, _, _ = subject_checker.build_diagnostic(
                schema_path=fixed[CONTEXT_SCHEMA].path, packet_path=private_context,
                explicit_carrier=private_carrier, repository_root=repository)
            require(code == 0 and context_diagnostic["ok"] is True,
                    "independent_subject_context_rejected", "context")
            packet = construct_packet(record=record, record_bytes=record_file.data, context=context,
                                      capture=capture, sources=bound_sources, dependencies=dependency_bytes,
                                      carrier_bytes=carrier_file.data, runtime=runtime)
            payload = canonical_bytes(packet)
            candidate = private / "packet.json"
            candidate.write_bytes(payload)
            diagnostic, code = runtime.build_diagnostic(schema_path=fixed[RUNTIME_SCHEMA].path, packet_path=candidate)
            require(code == 0 and diagnostic["ok"] is True, "independent_runtime_packet_rejected", "packet")
            require(candidate.read_bytes() == payload and private_context.read_bytes() == context_file.data
                    and private_carrier.read_bytes() == carrier_file.data,
                    "validator_mutated_temporary_input", "validation")
            recheck()
            publish_no_replace(output, payload, repository=repository, recheck=recheck)
        return {"tool": TOOL_NAME, "tool_version": TOOL_VERSION, "ok": True,
                "result": "historical_packet_published", "packet_sha256": sha256(payload),
                "packet_bytes": len(payload), "construction_sha256": construction_sha256,
                "capture_manifest_sha256": MANIFEST_SHA256, "job_records": 8, "step_records": 171,
                "collector_records": 1, "coverage_status": "partial", "authority_effect": "none",
                "same_run_release_authority_eligible": False, "active_gate_eligible": False}
    finally:
        os.close(repo_fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--capture-root", type=Path)
    parser.add_argument("--subject-context", type=Path)
    parser.add_argument("--carrier", type=Path)
    parser.add_argument("--construction-record", type=Path, required=True)
    parser.add_argument("--construction-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="New external JSON path; its parent must already exist.")
    args = parser.parse_args()
    try:
        result = build(repository_root=args.repository_root,
                       capture_root=args.capture_root or args.repository_root / CAPTURE_ROOT,
                       subject_context=args.subject_context or args.repository_root / CONTEXT_PATH,
                       carrier=args.carrier or args.repository_root / CARRIER_PATH,
                       construction_record=args.construction_record,
                       construction_sha256=args.construction_sha256, output=args.output)
    except Exception as exc:
        # Dependency diagnostics are classified without leaking raw payloads or
        # caller-controlled path/secret text into a nominally metadata-only result.
        code = getattr(exc, "code", getattr(exc, "error_code", "input_or_execution_failed"))
        stage = getattr(exc, "stage", "execution")
        result = {"tool": TOOL_NAME, "tool_version": TOOL_VERSION, "ok": False,
                  "error_code": code, "stage": stage, "authority_effect": "none"}
        sys.stderr.buffer.write(canonical_bytes(result))
        return 2
    sys.stdout.buffer.write(canonical_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
