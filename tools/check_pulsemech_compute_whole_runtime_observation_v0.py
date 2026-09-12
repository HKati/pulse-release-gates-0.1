#!/usr/bin/env python3
"""Independent Step 5C verifier and deterministic reconstruction entrypoint.

This tool is the network-free verifier for the prospective Step 5C whole-runtime
observation reference.  It never imports the plan builder, acquisition tool, or
capture builder and it never dispatches a workflow or repeats model inference.
It accepts only exact, already preserved inputs; reconstructs the derived
runtime packet and existing compute-binding/relation outputs; runs two separate
reconstruction processes; and publishes a verification record plus one closed
reference capsule without replacing an existing path.

Production sequence::

    python -I tools/check_pulsemech_compute_whole_runtime_observation_v0.py \
      prepare --repository-root . --source-commit <sha40> \
      --plan prelaunch-plan.json --plan-diagnostic plan-diagnostic.json \
      --expected-plan-sha256 <sha256> --output prepared.zip

    python -I tools/check_pulsemech_compute_whole_runtime_observation_v0.py \
      run-reference --repository-root . --source-commit <sha40> \
      --prepared prepared.zip --capture capture.zip \
      --expected-context expected_context.json \
      --expected-plan-digest expected-plan.sha256 \
      --output-directory <absent-directory>

The ``reconstruct`` subcommand is intentionally public for permanent regression
and independent replay.  All commands require isolated Python on Linux.
"""
from __future__ import annotations

import sys

if __name__ == "__main__" and not (
    sys.flags.isolated == 1
    and sys.flags.ignore_environment == 1
    and sys.flags.no_user_site == 1
    and bool(getattr(sys.flags, "safe_path", False))
):
    sys.stderr.write(
        '{"active_gate_eligible":false,"authority_effect":"none",'
        '"error_code":"isolated_python_required","ok":false,'
        '"same_run_release_authority_eligible":false,'
        '"tool":"check_pulsemech_compute_whole_runtime_observation_v0"}\n'
    )
    raise SystemExit(2)

import argparse
import ctypes
import datetime as dt
import errno
import hashlib
import io
import json
import math
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Iterable, Mapping, MutableMapping, Sequence

import jsonschema


TOOL_ID = "check_pulsemech_compute_whole_runtime_observation_v0"
TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = "pulsemech_compute_whole_runtime_observation_evidence_v0"
RUNTIME_SCHEMA_VERSION = "pulsemech_compute_runtime_observation_packet_v0"
PLAN_DIAGNOSTIC_VERSION = (
    "pulsemech_compute_whole_runtime_observation_plan_check_v0"
)
EXPECTED_CONTEXT_SCHEMA_VERSION = (
    "pulsemech_compute_whole_runtime_observation_expected_context_v0"
)
PROFILE = "pulse_ci_hosted_release_grade_v0"
SCOPE = "one_current_run_pulse_ci_hosted_release_grade_declared_workflow_graph_v0"
REPOSITORY = "HKati/pulse-release-gates-0.1"
SOURCE_REF = "refs/heads/main"
REFERENCE_WORKFLOW_NAME = (
    "PULSEmech compute whole-runtime observation reference"
)
REFERENCE_WORKFLOW_PATH = (
    ".github/workflows/pulsemech_compute_whole_runtime_observation_reference.yml"
)
SUBJECT_WORKFLOW_NAME = "PULSE CI"
SUBJECT_WORKFLOW_PATH = ".github/workflows/pulse_ci.yml"
PROVIDER_WORKFLOW_NAME = "PULSEmech compute current-run export candidate"
PROVIDER_WORKFLOW_PATH = (
    ".github/workflows/pulsemech_compute_current_run_export_candidate.yml"
)

VERIFIER_PATH = "tools/check_pulsemech_compute_whole_runtime_observation_v0.py"
SCHEMA_PATH = (
    "schemas/pulsemech_compute_whole_runtime_observation_evidence_v0.schema.json"
)
RUNTIME_SCHEMA_PATH = (
    "schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json"
)
RUNTIME_VALIDATOR_PATH = (
    "tools/check_pulsemech_compute_runtime_observation_packet_v0.py"
)
STEP3F_LOADER_PATH = (
    "tools/load_pulsemech_compute_current_run_export_candidate_bundle_v0.py"
)
STEP3G_PROOF_BUILDER_PATH = (
    "tools/build_pulsemech_compute_current_run_artifact_observed_proof_v0.py"
)
BINDING_BRIDGE_PATH = (
    "tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py"
)
BINDING_REPORT_SCHEMA_PATH = "schemas/pulsemech_compute_binding_report_v0.schema.json"
BINDING_REPORT_VALIDATOR_PATH = "tools/check_pulsemech_compute_binding_report_v0.py"
RELATION_BUILDER_PATH = "tools/build_pulsemech_compute_planned_observed_relation_v0.py"
RELATION_SCHEMA_PATH = "schemas/pulsemech_compute_planned_observed_relation_v0.schema.json"
RELATION_VALIDATOR_PATH = "tools/check_pulsemech_compute_planned_observed_relation_v0.py"
CANDIDATE_MATERIALIZER_PATH = (
    "tools/fold_pulsemech_compute_planned_observed_relation_into_status_v0.py"
)
POLICY_PATH = "pulse_gate_policy_v0.yml"
REGISTRY_PATH = "pulse_gate_registry_v0.yml"
EXTERNAL_SIGNER_POLICY_PATH = "policy/external_signers_v1.yml"
THRESHOLD_POLICY_PATH = "PULSE_safe_pack_v0/profiles/external_thresholds.yaml"
LLAMAGUARD_RAW_MEMBER = "artifacts/external/llamaguard_raw.jsonl"

PREPARED_PLAN_MEMBER = "prelaunch-plan.json"
PREPARED_DIAGNOSTIC_MEMBER = "prelaunch-plan-diagnostic.json"
PREPARED_DIGEST_MEMBER = "expected-plan.sha256"
PREPARED_SOURCE_INVENTORY_MEMBER = "source-inventory.json"
PREPARED_DISPATCH_INPUTS_MEMBER = "dispatch-inputs.json"
PREPARED_SOURCE_PREFIX = "sources/"
CAPTURE_MANIFEST_MEMBER = "capture.json"
CAPTURE_PROVIDER_ENVELOPE_MEMBER = (
    "acquisition/provider/step3f-candidate-envelope.zip"
)
CAPTURE_EXPECTED_CONTEXT_MEMBER = "acquisition/expected_context.json"
RECONSTRUCTION_INVENTORY_MEMBER = "reconstruction_inventory_v0.json"
VERIFICATION_RECORD_MEMBER = "verification_record_v0.json"
REFERENCE_CAPSULE_NAME = "reference_capsule_v0.zip"

RUNTIME_PACKET_MEMBER = "runtime-observation-packet.json"
RUNTIME_DIAGNOSTIC_MEMBER = "runtime-packet-diagnostic.json"
BINDING_REPORT_MEMBER = "compute-binding-report.json"
BINDING_DIAGNOSTIC_MEMBER = "binding-report-diagnostic.json"
RELATION_MEMBER = "planned-observed-relation.json"
RELATION_DIAGNOSTIC_MEMBER = "relation-diagnostic.json"
MATERIALIZER_REPORT_MEMBER = "candidate-materializer-report.json"
FOLDED_STATUS_MEMBER = "folded-candidate-status.json"

EXPECTED_JOB_COUNT = 8
EXPECTED_SUCCESSFUL_JOB_COUNT = 7
EXPECTED_SKIPPED_JOB_COUNT = 1
EXPECTED_STEP_TEMPLATE_COUNT = 147
EXPECTED_STEP_COUNT = 145
EXPECTED_SUCCESSFUL_STEP_COUNT = 101
EXPECTED_SKIPPED_STEP_COUNT = 44
EXPECTED_INFERENCE_COUNT = 6
EXPECTED_SUBJECT_EXECUTIONS = 153
EXPECTED_COLLECTOR_EXECUTIONS = 1
EXPECTED_TOTAL_EXECUTIONS = 154
EXPECTED_RESOURCE_MEASUREMENTS = 0

RESOURCE_AXES = sorted(
    {
        "runner_wall_seconds",
        "job_wall_seconds",
        "step_wall_seconds",
        "cpu_seconds",
        "gpu_seconds",
        "memory_gb_seconds",
        "network_bytes_sent",
        "network_bytes_received",
        "storage_bytes_written",
        "artifact_bytes_uploaded",
        "external_api_calls",
        "model_input_tokens",
        "model_output_tokens",
        "retry_count",
        "rerun_count",
    }
)
UNOBSERVED_REASONS = sorted(
    [
        "direct_child_process_extent_unavailable",
        "action_internal_operations_unavailable",
        "package_manager_activity_unavailable",
        "provider_internal_execution_unavailable",
        "per_inference_timing_partial",
        "resource_axis_unavailable",
    ]
)
GENERIC_UNOBSERVED_REASONS = sorted(
    [
        "external_provider_usage_unavailable",
        "model_content_digest_unavailable",
        "resource_axis_unavailable",
        "step_not_instrumented",
    ]
)

AUTHORITY_BOUNDARY: dict[str, Any] = {
    "authority_effect": "none",
    "same_run_release_authority_eligible": False,
    "active_gate_eligible": False,
    "changes_gate_policy": False,
    "changes_gate_registry": False,
    "changes_release_authority": False,
    "creates_compute_budget": False,
    "introduces_resource_measurement": False,
    "observer_in_subject_totals": False,
    "subject_artifacts_mutated": False,
    "writes_subject_status": False,
}
PRIVACY_BOUNDARY: dict[str, Any] = {
    "raw_environment_included": False,
    "secret_values_included": False,
    "authorization_headers_included": False,
    "cookies_included": False,
    "request_bodies_included": False,
    "response_bodies_included": False,
    "raw_prompt_text_included": False,
    "raw_model_output_included": False,
    "private_or_arbitrary_user_prompt_admitted": False,
    "opaque_controlled_fixture_payloads_present": True,
    "redaction_applied": False,
    "redaction_rules_sha256": None,
}
TRUST_BOUNDARY: dict[str, list[str]] = {
    "trusted_components": sorted(
        [
            "step5c_supervisor",
            "step5c_plan_builder",
            "step5c_plan_checker",
            "step5c_acquisition_tool",
            "step5c_capture_tool",
            "step5c_verifier",
            "cpython_runtime",
            "github_hosted_runner",
            "host_kernel",
            "github_control_plane",
            "pulse_ci_components",
            "step3f_components",
        ]
    ),
    "not_proven": sorted(
        [
            "privileged_host_integrity",
            "runner_image_integrity",
            "interpreter_integrity_against_privileged_host",
            "observer_integrity_against_privileged_host",
            "github_control_plane_integrity",
            "provider_internal_execution",
            "complete_network_activity",
            "complete_package_manager_activity",
        ]
    ),
}

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ZIP_MODE = stat.S_IFREG | 0o444
HASH_CHUNK = 1024 * 1024
MAX_JSON_BYTES = 64 * 1024 * 1024
MAX_PLAN_BYTES = 16 * 1024 * 1024
MAX_PREPARED_MEMBERS = 512
MAX_PREPARED_BYTES = 512 * 1024 * 1024
MAX_CAPTURE_MEMBERS = 8192
MAX_CAPTURE_BYTES = 2 * 1024 * 1024 * 1024
MAX_RECONSTRUCTION_MEMBERS = 16
MAX_RECONSTRUCTION_BYTES = 2 * 1024 * 1024 * 1024
MAX_PROCESS_STDOUT = 128 * 1024 * 1024
MAX_PROCESS_STDERR = 16 * 1024 * 1024
PROCESS_TIMEOUT_SECONDS = 900
FIXED_RECONSTRUCTION_ROOT = Path("/tmp/pulsemech-step5c-reconstruction-v0")

SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]+)?Z$"
)


class VerificationError(RuntimeError):
    """Stable fail-closed diagnostic without unbounded input excerpts."""

    def __init__(self, code: str, detail: str | None = None, *, stage: str = "verify") -> None:
        super().__init__(code if detail is None else f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.stage = stage


class StrictJsonError(VerificationError):
    pass


@dataclass(frozen=True)
class FileDescriptor:
    member: str
    sha256: str
    size_bytes: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "member": self.member,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class SourceDescriptor:
    role: str
    path: str
    revision: str
    git_blob_sha1: str
    sha256: str
    size_bytes: int
    executable: bool


@dataclass(frozen=True)
class ZipMember:
    name: str
    sha256: str
    size_bytes: int
    data: bytes | None = None


@dataclass(frozen=True)
class ReconstructionResult:
    output: Path
    sha256: str
    size_bytes: int
    inventory_sha256: str
    inventory_size_bytes: int
    process_id: int
    process_run_key: str


@dataclass(frozen=True)
class ProcessOutput:
    returncode: int
    stdout: bytes
    stderr: bytes


def require(condition: bool, code: str, detail: str | None = None, *, stage: str = "verify") -> None:
    if not condition:
        raise VerificationError(code, detail, stage=stage)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(HASH_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def canonical_json_bytes(value: Any) -> bytes:
    def check(item: Any) -> None:
        if isinstance(item, str):
            require(unicodedata.normalize("NFC", item) == item, "non_nfc_json_string", stage="json")
        elif isinstance(item, dict):
            for key, child in item.items():
                require(isinstance(key, str), "json_key_not_string", stage="json")
                check(key)
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)
        elif item is None or type(item) in {bool, int}:
            return
        elif isinstance(item, float):
            require(math.isfinite(item), "non_finite_json_number", stage="json")
        else:
            raise VerificationError("unsupported_json_type", type(item).__name__, stage="json")

    check(value)
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError("duplicate_json_key", key, stage="json")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise StrictJsonError("non_finite_json_number", value, stage="json")


def parse_json_bytes(
    raw: bytes,
    *,
    label: str,
    canonical: bool = True,
    maximum: int = MAX_JSON_BYTES,
) -> dict[str, Any]:
    require(isinstance(raw, bytes) and len(raw) <= maximum, "json_size_out_of_range", label, stage="json")
    require(not raw.startswith(b"\xef\xbb\xbf"), "json_bom_rejected", label, stage="json")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite,
        )
    except VerificationError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise StrictJsonError("invalid_json", label, stage="json") from exc
    require(isinstance(value, dict), "json_object_required", label, stage="json")
    if canonical:
        require(canonical_json_bytes(value) == raw, "noncanonical_json", label, stage="json")
    return value


def parse_utc(value: Any, *, label: str) -> dt.datetime:
    require(isinstance(value, str) and UTC_RE.fullmatch(value) is not None, "invalid_utc", label, stage="time")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise VerificationError("invalid_utc", label, stage="time") from exc
    return parsed.astimezone(dt.timezone.utc)


def duration_ms(started: str | None, completed: str | None) -> int | None:
    if started is None or completed is None:
        return None
    delta = parse_utc(completed, label="completed") - parse_utc(started, label="started")
    require(delta.total_seconds() >= 0, "negative_duration", stage="time")
    return int(round(delta.total_seconds() * 1000.0))


def canonical_sha40(value: Any, *, label: str) -> str:
    require(isinstance(value, str) and SHA40_RE.fullmatch(value) is not None, "invalid_sha40", label, stage="identity")
    return value


def canonical_sha256(value: Any, *, label: str) -> str:
    require(isinstance(value, str) and SHA256_RE.fullmatch(value) is not None, "invalid_sha256", label, stage="identity")
    return value


def positive_int(value: Any, *, label: str) -> int:
    require(type(value) is int and value > 0, "positive_integer_required", label, stage="identity")
    return value


def safe_member(value: Any, *, label: str) -> str:
    require(isinstance(value, str) and value != "" and len(value) <= 500, "unsafe_member", label, stage="archive")
    require("\\" not in value and "\x00" not in value and not value.endswith("/"), "unsafe_member", label, stage="archive")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value, "unsafe_member", label, stage="archive")
    require(all(part not in {"", ".", ".."} for part in path.parts), "unsafe_member", label, stage="archive")
    return value


def descriptor(member: str, raw: bytes) -> dict[str, Any]:
    return FileDescriptor(safe_member(member, label="descriptor.member"), sha256_bytes(raw), len(raw)).as_dict()


def file_descriptor(member: str, path: Path) -> dict[str, Any]:
    digest, size = sha256_file(path)
    return FileDescriptor(safe_member(member, label="descriptor.member"), digest, size).as_dict()


def _git_environment(home: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "LANG": "C",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
    }


def git(root: Path, args: Sequence[str], *, timeout: int = 60, max_bytes: int = 128 * 1024 * 1024) -> bytes:
    command = [
        "/usr/bin/git",
        "--no-pager",
        "--no-replace-objects",
        "--no-lazy-fetch",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "credential.helper=",
        "-c",
        "credential.interactive=false",
        "-c",
        "protocol.allow=never",
        "-c",
        f"safe.directory={root}",
        "-C",
        str(root),
        *args,
    ]
    try:
        process = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            env=_git_environment(root),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VerificationError("git_execution_failed", stage="source") from exc
    require(process.returncode == 0, "git_command_failed", process.stderr.decode("utf-8", errors="replace")[:1000], stage="source")
    require(len(process.stdout) <= max_bytes, "git_output_too_large", stage="source")
    return process.stdout


def validate_repository(root: Path, source_commit: str) -> Path:
    candidate = Path(os.path.abspath(os.fspath(root)))
    require(candidate.is_dir() and not candidate.is_symlink(), "repository_root_invalid", str(candidate), stage="source")
    revision = canonical_sha40(source_commit, label="source_commit")
    require(git(candidate, ["cat-file", "-t", revision], max_bytes=1024) == b"commit\n", "source_commit_object_required", stage="source")
    top = Path(git(candidate, ["rev-parse", "--show-toplevel"], max_bytes=4096).decode("utf-8").strip())
    require(top.resolve() == candidate.resolve(), "repository_root_mismatch", stage="source")
    head = git(candidate, ["rev-parse", "HEAD"], max_bytes=4096).decode("ascii").strip().lower()
    require(head == revision, "checked_out_head_mismatch", f"{head}!={revision}", stage="source")
    return candidate


def git_blob(root: Path, revision: str, relative: str, *, maximum: int = 16 * 1024 * 1024) -> tuple[bytes, str, bool]:
    path = safe_member(relative, label="source.path")
    listing = git(root, ["ls-tree", "-z", revision, "--", path], max_bytes=64 * 1024)
    rows = [row for row in listing.split(b"\x00") if row]
    require(len(rows) == 1, "source_tree_entry_not_unique", path, stage="source")
    try:
        meta, raw_path = rows[0].split(b"\t", 1)
        mode, kind, oid = meta.decode("ascii").split(" ")
        decoded = raw_path.decode("utf-8", errors="strict")
    except Exception as exc:
        raise VerificationError("source_tree_entry_invalid", path, stage="source") from exc
    require(decoded == path and kind == "blob" and mode in {"100644", "100755"}, "source_not_regular_blob", path, stage="source")
    raw = git(root, ["cat-file", "blob", oid], max_bytes=maximum)
    require(len(raw) <= maximum, "source_blob_too_large", path, stage="source")
    framed = b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
    require(hashlib.sha1(framed).hexdigest() == oid, "source_blob_identity_mismatch", path, stage="source")
    return raw, oid, mode == "100755"


def source_inventory_map(plan: Mapping[str, Any]) -> dict[str, SourceDescriptor]:
    rows = plan.get("source_inventory")
    require(isinstance(rows, list) and rows, "plan_source_inventory_missing", stage="plan")
    result: dict[str, SourceDescriptor] = {}
    for row in rows:
        require(isinstance(row, dict), "plan_source_descriptor_invalid", stage="plan")
        path = safe_member(row.get("path"), label="plan.source.path")
        require(path not in result, "plan_source_path_duplicate", path, stage="plan")
        result[path] = SourceDescriptor(
            role=str(row.get("role")),
            path=path,
            revision=canonical_sha40(row.get("revision"), label=f"source:{path}:revision"),
            git_blob_sha1=canonical_sha40(row.get("git_blob_sha1"), label=f"source:{path}:blob"),
            sha256=canonical_sha256(row.get("sha256"), label=f"source:{path}:sha256"),
            size_bytes=positive_int(row.get("size_bytes"), label=f"source:{path}:size"),
            executable=bool(row.get("executable")),
        )
    return result


def verify_source_inventory(root: Path, source_commit: str, plan: Mapping[str, Any]) -> dict[str, bytes]:
    inventory = source_inventory_map(plan)
    required = {
        VERIFIER_PATH,
        SCHEMA_PATH,
        RUNTIME_SCHEMA_PATH,
        RUNTIME_VALIDATOR_PATH,
        STEP3F_LOADER_PATH,
        STEP3G_PROOF_BUILDER_PATH,
        BINDING_BRIDGE_PATH,
        BINDING_REPORT_SCHEMA_PATH,
        BINDING_REPORT_VALIDATOR_PATH,
        RELATION_BUILDER_PATH,
        RELATION_SCHEMA_PATH,
        RELATION_VALIDATOR_PATH,
        CANDIDATE_MATERIALIZER_PATH,
        SUBJECT_WORKFLOW_PATH,
        PROVIDER_WORKFLOW_PATH,
        POLICY_PATH,
        REGISTRY_PATH,
    }
    require(required.issubset(inventory), "required_source_missing", ",".join(sorted(required - set(inventory))), stage="source")
    result: dict[str, bytes] = {}
    for path, expected in sorted(inventory.items()):
        require(expected.revision == source_commit, "source_revision_mismatch", path, stage="source")
        raw, oid, executable = git_blob(root, source_commit, path)
        require(oid == expected.git_blob_sha1, "source_blob_mismatch", path, stage="source")
        require(sha256_bytes(raw) == expected.sha256, "source_digest_mismatch", path, stage="source")
        require(len(raw) == expected.size_bytes, "source_size_mismatch", path, stage="source")
        require(executable == expected.executable, "source_mode_mismatch", path, stage="source")
        result[path] = raw
    current = Path(__file__).resolve()
    expected_current = (root / VERIFIER_PATH).resolve()
    require(current == expected_current, "verifier_installation_path_mismatch", stage="source")
    require(current.read_bytes() == result[VERIFIER_PATH], "verifier_worktree_source_mismatch", stage="source")
    return result


def parse_source_schema(raw: bytes) -> dict[str, Any]:
    """Read exact source bytes without imposing generated-record formatting."""
    schema = parse_json_bytes(raw, label="step5c_schema", canonical=False)
    # Keep the NFC and supported-value checks that canonical record parsing
    # supplies, but do not rewrite or compare the Git-bound source formatting.
    canonical_json_bytes(schema)
    return schema


def validate_schema(schema: Mapping[str, Any], document: Mapping[str, Any], *, label: str) -> None:
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
        )
        errors = sorted(
            validator.iter_errors(document),
            key=lambda item: [str(part) for part in item.absolute_path],
        )
    except Exception as exc:
        raise VerificationError("schema_validation_failed", label, stage="schema") from exc
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise VerificationError("schema_rejected", f"{label}:{location}:{first.validator}", stage="schema")


def _zip_info(name: str) -> zipfile.ZipInfo:
    member = safe_member(name, label="zip.member")
    info = zipfile.ZipInfo(member, date_time=ZIP_TIMESTAMP)
    info.create_system = 3
    info.external_attr = ZIP_MODE << 16
    info.compress_type = zipfile.ZIP_STORED
    info.flag_bits = 0
    info.extra = b""
    info.comment = b""
    return info


def deterministic_zip_bytes(members: Mapping[str, bytes], *, maximum_members: int, maximum_bytes: int) -> bytes:
    require(0 < len(members) <= maximum_members, "zip_member_count_invalid", stage="archive")
    total = 0
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for name, raw in sorted(members.items()):
            safe_member(name, label="zip.member")
            require(isinstance(raw, bytes), "zip_member_not_bytes", name, stage="archive")
            total += len(raw)
            require(total <= maximum_bytes, "zip_total_size_exceeded", stage="archive")
            archive.writestr(_zip_info(name), raw)
    return stream.getvalue()


def read_canonical_zip_bytes(
    raw: bytes,
    *,
    label: str,
    maximum_members: int,
    maximum_bytes: int,
) -> dict[str, bytes]:
    require(len(raw) <= maximum_bytes + 64 * 1024 * 1024, "zip_file_too_large", label, stage="archive")
    result: dict[str, bytes] = {}
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            infos = archive.infolist()
            require(0 < len(infos) <= maximum_members, "zip_member_count_invalid", label, stage="archive")
            for info in infos:
                name = safe_member(info.filename, label=f"{label}.member")
                require(name not in result, "zip_duplicate_member", name, stage="archive")
                mode = (info.external_attr >> 16) & 0xFFFF
                require(not info.is_dir() and stat.S_ISREG(mode), "zip_nonregular_member", name, stage="archive")
                require(info.compress_type == zipfile.ZIP_STORED, "zip_not_stored", name, stage="archive")
                require(info.flag_bits & 1 == 0 and info.extra == b"" and info.comment == b"", "zip_metadata_invalid", name, stage="archive")
                require(tuple(info.date_time) == ZIP_TIMESTAMP, "zip_timestamp_mismatch", name, stage="archive")
                require(stat.S_IMODE(mode) == 0o444, "zip_mode_mismatch", name, stage="archive")
                total += info.file_size
                require(total <= maximum_bytes, "zip_total_size_exceeded", label, stage="archive")
                payload = archive.read(info)
                require(len(payload) == info.file_size, "zip_member_size_mismatch", name, stage="archive")
                result[name] = payload
    except VerificationError:
        raise
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError) as exc:
        raise VerificationError("invalid_zip", label, stage="archive") from exc
    require(deterministic_zip_bytes(result, maximum_members=maximum_members, maximum_bytes=maximum_bytes) == raw, "zip_not_canonical", label, stage="archive")
    return result


def _copy_stream(source: BinaryIO, target: BinaryIO, *, maximum: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    while True:
        chunk = source.read(HASH_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        require(total <= maximum, "stream_size_exceeded", stage="archive")
        digest.update(chunk)
        target.write(chunk)
    return digest.hexdigest(), total


def _rename_noreplace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise VerificationError("rename_noreplace_unavailable", stage="output")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        -100,
        os.fsencode(source),
        -100,
        os.fsencode(destination),
        1,
    )
    if result != 0:
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise VerificationError("output_already_exists", str(destination), stage="output")
        raise VerificationError("rename_noreplace_failed", os.strerror(error), stage="output")


def publish_bytes(path: Path, raw: bytes, *, mode: int = 0o444) -> tuple[str, int]:
    destination = Path(os.path.abspath(os.fspath(path)))
    require(not destination.exists() and not destination.is_symlink(), "output_already_exists", str(destination), stage="output")
    require(destination.parent.is_dir() and not destination.parent.is_symlink(), "output_parent_invalid", str(destination.parent), stage="output")
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        _rename_noreplace(temporary, destination)
        temporary = None
        parent_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass
    return sha256_bytes(raw), len(raw)


def publish_zip_from_files(path: Path, members: Mapping[str, Path | bytes]) -> tuple[str, int]:
    destination = Path(os.path.abspath(os.fspath(path)))
    require(not destination.exists() and not destination.is_symlink(), "output_already_exists", str(destination), stage="output")
    require(destination.parent.is_dir(), "output_parent_invalid", stage="output")
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
        os.close(descriptor)
        temporary = Path(name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for member, source in sorted(members.items()):
                info = _zip_info(member)
                if isinstance(source, bytes):
                    archive.writestr(info, source)
                else:
                    with source.open("rb") as input_stream, archive.open(info, "w", force_zip64=True) as output_stream:
                        _copy_stream(input_stream, output_stream, maximum=MAX_CAPTURE_BYTES)
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        temporary.chmod(0o444)
        _rename_noreplace(temporary, destination)
        temporary = None
        parent_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass
    return sha256_file(destination)


def expected_plan_digest_bytes(value: str) -> bytes:
    digest = canonical_sha256(value.strip(), label="expected_plan_sha256")
    return (digest + "\n").encode("ascii")


def validate_plan_and_diagnostic(
    *,
    plan_raw: bytes,
    diagnostic_raw: bytes,
    expected_digest: str,
    source_commit: str,
    record_status: str,
    schema: Mapping[str, Any],
) -> dict[str, Any]:
    require(sha256_bytes(plan_raw) == expected_digest, "plan_digest_mismatch", stage="plan")
    plan = parse_json_bytes(plan_raw, label="prelaunch_plan", maximum=MAX_PLAN_BYTES)
    validate_schema(schema, plan, label="prelaunch_plan")
    identity = plan.get("plan_identity")
    require(isinstance(identity, dict), "plan_identity_missing", stage="plan")
    require(plan.get("record_type") == "prelaunch_plan", "plan_record_type_mismatch", stage="plan")
    require(plan.get("record_status") == record_status, "plan_record_status_mismatch", stage="plan")
    require(identity.get("profile") == PROFILE and identity.get("scope") == SCOPE, "plan_scope_mismatch", stage="plan")
    require(identity.get("repository") == REPOSITORY and identity.get("source_commit") == source_commit, "plan_source_mismatch", stage="plan")
    require(plan.get("authority_boundary") == AUTHORITY_BOUNDARY, "plan_authority_boundary_mismatch", stage="plan")
    require(plan.get("privacy_boundary") == PRIVACY_BOUNDARY, "plan_privacy_boundary_mismatch", stage="plan")
    require(plan.get("trust_boundary") == TRUST_BOUNDARY, "plan_trust_boundary_mismatch", stage="plan")
    terminal = plan.get("terminal_counts")
    require(
        terminal == {
            "job_templates": EXPECTED_JOB_COUNT,
            "successful_jobs": EXPECTED_SUCCESSFUL_JOB_COUNT,
            "permitted_skipped_jobs": EXPECTED_SKIPPED_JOB_COUNT,
            "step_templates": EXPECTED_STEP_TEMPLATE_COUNT,
            "instantiated_steps": EXPECTED_STEP_COUNT,
            "successful_steps": EXPECTED_SUCCESSFUL_STEP_COUNT,
            "permitted_skipped_steps": EXPECTED_SKIPPED_STEP_COUNT,
            "uninstantiated_steps": 2,
            "model_inference_occurrences": EXPECTED_INFERENCE_COUNT,
        },
        "plan_terminal_counts_mismatch",
        stage="plan",
    )
    diagnostic = parse_json_bytes(diagnostic_raw, label="plan_diagnostic")
    require(diagnostic.get("schema_version") == PLAN_DIAGNOSTIC_VERSION, "plan_diagnostic_version_mismatch", stage="plan")
    require(diagnostic.get("ok") is True and diagnostic.get("record_status") == "verified", "plan_diagnostic_not_verified", stage="plan")
    binding = diagnostic.get("plan")
    require(isinstance(binding, dict), "plan_diagnostic_binding_missing", stage="plan")
    require(binding.get("sha256") == expected_digest and binding.get("source_commit") == source_commit, "plan_diagnostic_binding_mismatch", stage="plan")
    require(binding.get("byte_identical_to_independent_reconstruction") is True, "plan_independent_reconstruction_missing", stage="plan")
    require(diagnostic.get("authority_boundary") == AUTHORITY_BOUNDARY, "plan_diagnostic_authority_mismatch", stage="plan")
    return plan


def prepare_carrier(
    *,
    repository_root: Path,
    source_commit: str,
    plan_path: Path,
    diagnostic_path: Path,
    expected_plan_sha256: str,
    output: Path,
    record_status: str,
) -> dict[str, Any]:
    root = validate_repository(repository_root, source_commit)
    plan_raw = plan_path.read_bytes()
    diagnostic_raw = diagnostic_path.read_bytes()
    schema_raw, _oid, _exec = git_blob(root, source_commit, SCHEMA_PATH)
    schema = parse_source_schema(schema_raw)
    plan = validate_plan_and_diagnostic(
        plan_raw=plan_raw,
        diagnostic_raw=diagnostic_raw,
        expected_digest=canonical_sha256(expected_plan_sha256, label="expected_plan_sha256"),
        source_commit=source_commit,
        record_status=record_status,
        schema=schema,
    )
    sources = verify_source_inventory(root, source_commit, plan)
    source_rows = plan["source_inventory"]
    members: dict[str, bytes] = {
        PREPARED_PLAN_MEMBER: plan_raw,
        PREPARED_DIAGNOSTIC_MEMBER: diagnostic_raw,
        PREPARED_DIGEST_MEMBER: expected_plan_digest_bytes(expected_plan_sha256),
        PREPARED_SOURCE_INVENTORY_MEMBER: canonical_json_bytes(
            {
                "schema_version": "pulsemech_compute_whole_runtime_observation_prepared_sources_v0",
                "record_status": record_status,
                "repository": REPOSITORY,
                "source_commit": source_commit,
                "members": source_rows,
                "authority_boundary": AUTHORITY_BOUNDARY,
                "errors": [],
                "ok": True,
            }
        ),
        PREPARED_DISPATCH_INPUTS_MEMBER: canonical_json_bytes(
            {
                "subject": plan["subject_dispatch"],
                "provider": plan["provider_dispatch"],
                "authority_boundary": AUTHORITY_BOUNDARY,
            }
        ),
    }
    for path, raw in sources.items():
        members[PREPARED_SOURCE_PREFIX + path] = raw
    prepared = deterministic_zip_bytes(
        members,
        maximum_members=MAX_PREPARED_MEMBERS,
        maximum_bytes=MAX_PREPARED_BYTES,
    )
    digest, size = publish_bytes(output, prepared)
    return {
        "tool": TOOL_ID,
        "version": TOOL_VERSION,
        "mode": "prepare",
        "record_status": record_status,
        "ok": True,
        "output": str(Path(output).absolute()),
        "output_sha256": digest,
        "output_size_bytes": size,
        "member_count": len(members),
        "authority_boundary": AUTHORITY_BOUNDARY,
        "errors": [],
    }


def read_prepared(path: Path, *, source_commit: str, expected_digest: str, record_status: str, schema: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, bytes], bytes]:
    raw = path.read_bytes()
    members = read_canonical_zip_bytes(
        raw,
        label="prepared_carrier",
        maximum_members=MAX_PREPARED_MEMBERS,
        maximum_bytes=MAX_PREPARED_BYTES,
    )
    required = {
        PREPARED_PLAN_MEMBER,
        PREPARED_DIAGNOSTIC_MEMBER,
        PREPARED_DIGEST_MEMBER,
        PREPARED_SOURCE_INVENTORY_MEMBER,
        PREPARED_DISPATCH_INPUTS_MEMBER,
    }
    require(required.issubset(members), "prepared_member_missing", stage="prepared")
    require(members[PREPARED_DIGEST_MEMBER] == expected_plan_digest_bytes(expected_digest), "prepared_expected_digest_mismatch", stage="prepared")
    plan = validate_plan_and_diagnostic(
        plan_raw=members[PREPARED_PLAN_MEMBER],
        diagnostic_raw=members[PREPARED_DIAGNOSTIC_MEMBER],
        expected_digest=expected_digest,
        source_commit=source_commit,
        record_status=record_status,
        schema=schema,
    )
    inventory = source_inventory_map(plan)
    expected_source_members = {PREPARED_SOURCE_PREFIX + path for path in inventory}
    require(expected_source_members.issubset(members), "prepared_source_member_missing", stage="prepared")
    require(
        set(members) == required | expected_source_members,
        "prepared_member_inventory_mismatch",
        stage="prepared",
    )
    for path, row in inventory.items():
        source_member = PREPARED_SOURCE_PREFIX + path
        payload = members[source_member]
        require(sha256_bytes(payload) == row.sha256 and len(payload) == row.size_bytes, "prepared_source_identity_mismatch", path, stage="prepared")
    source_record = parse_json_bytes(members[PREPARED_SOURCE_INVENTORY_MEMBER], label="prepared_source_inventory")
    expected_source_record = {
        "schema_version": "pulsemech_compute_whole_runtime_observation_prepared_sources_v0",
        "record_status": record_status,
        "repository": REPOSITORY,
        "source_commit": source_commit,
        "members": plan["source_inventory"],
        "authority_boundary": AUTHORITY_BOUNDARY,
        "errors": [],
        "ok": True,
    }
    require(
        canonical_json_bytes(source_record) == canonical_json_bytes(expected_source_record),
        "prepared_source_inventory_mismatch",
        stage="prepared",
    )
    dispatch_inputs = parse_json_bytes(
        members[PREPARED_DISPATCH_INPUTS_MEMBER], label="prepared_dispatch_inputs"
    )
    expected_dispatch_inputs = {
        "subject": plan["subject_dispatch"],
        "provider": plan["provider_dispatch"],
        "authority_boundary": AUTHORITY_BOUNDARY,
    }
    require(
        canonical_json_bytes(dispatch_inputs) == canonical_json_bytes(expected_dispatch_inputs),
        "prepared_dispatch_inputs_mismatch",
        stage="prepared",
    )
    return plan, members, raw


def read_capture(path: Path, *, schema: Mapping[str, Any], plan: Mapping[str, Any], expected_plan_sha256: str, expected_context_raw: bytes, record_status: str, source_commit: str) -> tuple[dict[str, Any], dict[str, bytes], bytes]:
    raw = path.read_bytes()
    members = read_canonical_zip_bytes(
        raw,
        label="capture_carrier",
        maximum_members=MAX_CAPTURE_MEMBERS,
        maximum_bytes=MAX_CAPTURE_BYTES,
    )
    require(CAPTURE_MANIFEST_MEMBER in members, "capture_manifest_missing", stage="capture")
    manifest = parse_json_bytes(members[CAPTURE_MANIFEST_MEMBER], label="capture_manifest")
    validate_schema(schema, manifest, label="capture_manifest")
    require(manifest.get("record_type") == "capture_manifest" and manifest.get("record_status") == record_status, "capture_record_status_mismatch", stage="capture")
    identity = manifest.get("capture_identity")
    require(isinstance(identity, dict), "capture_identity_missing", stage="capture")
    require(identity.get("profile") == PROFILE and identity.get("scope") == SCOPE, "capture_scope_mismatch", stage="capture")
    require(identity.get("source_commit") == source_commit and identity.get("repository") == REPOSITORY, "capture_source_mismatch", stage="capture")
    require(manifest.get("authority_boundary") == AUTHORITY_BOUNDARY, "capture_authority_boundary_mismatch", stage="capture")
    require(manifest.get("privacy_boundary") == PRIVACY_BOUNDARY and manifest.get("trust_boundary") == TRUST_BOUNDARY, "capture_boundary_mismatch", stage="capture")
    require(manifest.get("content_boundary", {}).get("verifier_verdict_included") is False, "capture_contains_verifier_verdict", stage="capture")
    require(manifest.get("content_boundary", {}).get("runtime_packet_included") is False, "capture_contains_runtime_packet", stage="capture")
    inventory = manifest.get("member_inventory")
    require(isinstance(inventory, dict) and inventory.get("manifest_scope") == "all_capture_members_except_this_manifest", "capture_inventory_scope_mismatch", stage="capture")
    rows = inventory.get("members")
    require(isinstance(rows, list), "capture_inventory_missing", stage="capture")
    declared: dict[str, dict[str, Any]] = {}
    for row in rows:
        require(isinstance(row, dict), "capture_inventory_row_invalid", stage="capture")
        member = safe_member(row.get("member"), label="capture.inventory.member")
        require(member not in declared, "capture_inventory_duplicate", member, stage="capture")
        declared[member] = row
    actual = set(members) - {CAPTURE_MANIFEST_MEMBER}
    require(set(declared) == actual and inventory.get("member_count") == len(actual), "capture_inventory_mismatch", stage="capture")
    for member, row in declared.items():
        payload = members[member]
        require(row.get("sha256") == sha256_bytes(payload) and row.get("size_bytes") == len(payload), "capture_member_identity_mismatch", member, stage="capture")
    binding = manifest.get("plan_binding")
    require(isinstance(binding, dict), "capture_plan_binding_missing", stage="capture")
    require(binding.get("expected_plan_sha256") == expected_plan_sha256, "capture_plan_digest_mismatch", stage="capture")
    require(members.get("prepared/prelaunch-plan.json") == canonical_json_bytes(plan), "capture_plan_bytes_mismatch", stage="capture")
    require(members.get(CAPTURE_EXPECTED_CONTEXT_MEMBER) == expected_context_raw, "capture_expected_context_mismatch", stage="capture")
    counts = manifest.get("platform_counts")
    require(isinstance(counts, dict), "capture_platform_counts_missing", stage="capture")
    expected_counts = {
        "expected_job_count": EXPECTED_JOB_COUNT,
        "observed_job_count": EXPECTED_JOB_COUNT,
        "successful_job_count": EXPECTED_SUCCESSFUL_JOB_COUNT,
        "skipped_job_count": EXPECTED_SKIPPED_JOB_COUNT,
        "expected_step_template_count": EXPECTED_STEP_TEMPLATE_COUNT,
        "expected_instantiated_step_count": EXPECTED_STEP_COUNT,
        "observed_declared_step_count": EXPECTED_STEP_COUNT,
        "successful_declared_step_count": EXPECTED_SUCCESSFUL_STEP_COUNT,
        "skipped_declared_step_count": EXPECTED_SKIPPED_STEP_COUNT,
        "subject_execution_record_count": EXPECTED_SUBJECT_EXECUTIONS,
        "collector_execution_record_count": EXPECTED_COLLECTOR_EXECUTIONS,
        "total_runtime_execution_record_count": EXPECTED_TOTAL_EXECUTIONS,
        "model_inference_record_count": EXPECTED_INFERENCE_COUNT,
        "resource_measurement_record_count": EXPECTED_RESOURCE_MEASUREMENTS,
    }
    for key, value in expected_counts.items():
        require(counts.get(key) == value, "capture_platform_count_mismatch", key, stage="capture")
    subject = manifest.get("subject")
    provider = manifest.get("provider")
    require(isinstance(subject, dict) and isinstance(provider, dict), "capture_run_summary_missing", stage="capture")
    require(subject.get("run_attempt") == provider.get("run_attempt") == 1, "capture_attempt_mismatch", stage="capture")
    require(subject.get("head_sha") == provider.get("head_sha") == source_commit, "capture_run_source_mismatch", stage="capture")
    require(CAPTURE_PROVIDER_ENVELOPE_MEMBER in members, "provider_envelope_missing", stage="capture")
    return manifest, members, raw


def _expected_context(raw: bytes, *, source_commit: str, expected_plan_sha256: str, record_status: str) -> dict[str, Any]:
    context = parse_json_bytes(raw, label="expected_context")
    expected = {
        "schema_version": EXPECTED_CONTEXT_SCHEMA_VERSION,
        "record_status": record_status,
        "repository": REPOSITORY,
        "source_commit": source_commit,
        "source_ref": SOURCE_REF,
        "reference_workflow_name": REFERENCE_WORKFLOW_NAME,
        "reference_workflow_path": REFERENCE_WORKFLOW_PATH,
        "reference_run_attempt": 1,
        "expected_plan_sha256": expected_plan_sha256,
        "authority_boundary": AUTHORITY_BOUNDARY,
        "errors": [],
        "ok": True,
    }
    for key, value in expected.items():
        require(context.get(key) == value, "expected_context_mismatch", key, stage="context")
    positive_int(context.get("reference_run_id"), label="reference_run_id")
    positive_int(context.get("reference_run_number"), label="reference_run_number")
    return context


def _capture_job_rows(capture_members: Mapping[str, bytes], manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    bindings = manifest.get("raw_response_bindings")
    require(isinstance(bindings, list), "raw_response_bindings_missing", stage="capture")
    members = [
        row.get("descriptor", {}).get("member")
        for row in bindings
        if isinstance(row, dict) and row.get("role") == "subject_jobs_page"
    ]
    rows: list[dict[str, Any]] = []
    for member in members:
        require(isinstance(member, str) and member in capture_members, "subject_jobs_page_missing", stage="capture")
        page = parse_json_bytes(capture_members[member], label="subject_jobs_page", canonical=False)
        values = page.get("jobs")
        require(isinstance(values, list), "subject_jobs_array_missing", stage="capture")
        rows.extend(value for value in values if isinstance(value, dict))
    require(len(rows) == EXPECTED_JOB_COUNT, "subject_job_extent_mismatch", stage="capture")
    return rows


def _source_row(plan: Mapping[str, Any], path: str) -> Mapping[str, Any]:
    for row in plan.get("source_inventory", []):
        if isinstance(row, dict) and row.get("path") == path:
            return row
    raise VerificationError("plan_source_missing", path, stage="plan")


def _empty_source_identity() -> dict[str, Any]:
    return {
        "identity_status": "unknown",
        "source_kind": "unknown",
        "source_path_or_uri": None,
        "source_revision": None,
        "source_sha256": None,
        "action_repository": None,
        "action_ref": None,
        "action_commit_sha": None,
        "container_image_digest": None,
    }


def _repository_source(plan: Mapping[str, Any], path: str, *, status: str = "exact") -> dict[str, Any]:
    row = _source_row(plan, path)
    return {
        "identity_status": status,
        "source_kind": "repository_file",
        "source_path_or_uri": path,
        "source_revision": row.get("revision"),
        "source_sha256": row.get("sha256"),
        "action_repository": None,
        "action_ref": None,
        "action_commit_sha": None,
        "container_image_digest": None,
    }


def _action_source(source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "identity_status": "exact",
        "source_kind": "github_action",
        "source_path_or_uri": str(source.get("uses")),
        "source_revision": None,
        "source_sha256": None,
        "action_repository": source.get("action_repository"),
        "action_ref": source.get("action_ref"),
        "action_commit_sha": source.get("action_commit_sha"),
        "container_image_digest": None,
    }


def _unknown_command() -> dict[str, Any]:
    return {
        "command_kind": "unknown",
        "display_name": "command not observed",
        "command_sha256": None,
        "arguments_sha256": None,
        "raw_command_included": False,
    }


def _step_command(source: Mapping[str, Any]) -> dict[str, Any]:
    # These are source-template identities, not traces of action internals or
    # of the expanded runtime arguments of a shell block.
    if source.get("kind") == "github_action":
        return {
            "command_kind": "github_action",
            "display_name": str(source.get("uses")),
            "command_sha256": sha256_bytes(canonical_json_bytes(source)),
            "arguments_sha256": None,
            "raw_command_included": False,
        }
    if source.get("kind") == "shell":
        return {
            "command_kind": "shell",
            "display_name": str(source.get("shell")),
            "command_sha256": canonical_sha256(source.get("run_sha256"), label="step_command"),
            "arguments_sha256": None,
            "raw_command_included": False,
        }
    raise VerificationError("command_source_mismatch", stage="runtime")


def _timing(started: Any, completed: Any, *, partial: bool = False) -> dict[str, Any]:
    start = started if isinstance(started, str) and UTC_RE.fullmatch(started) else None
    finish = completed if isinstance(completed, str) and UTC_RE.fullmatch(completed) else None
    if start is None or finish is None:
        return {
            "timing_status": "unknown",
            "started_utc": None,
            "completed_utc": None,
            "duration_ms": None,
            "timestamp_source": "unknown",
            "duration_source": "unknown",
        }
    return {
        "timing_status": "partial" if partial else "complete",
        "started_utc": start,
        "completed_utc": finish,
        "duration_ms": duration_ms(start, finish),
        "timestamp_source": "platform_reported",
        "duration_source": "derived_from_timestamps",
    }


def _execution_environment() -> dict[str, Any]:
    # The accepted profile uses hosted runners. Their concrete image, runtime
    # versions and architecture are not established by a runs-on source label.
    return {
        "environment_kind": "github_hosted_runner",
        "identity_status": "partial",
        "os_name": None,
        "os_version": None,
        "architecture": None,
        "runtime_name": None,
        "runtime_version": None,
        "image_identity": None,
        "image_digest": None,
        "environment_sha256": None,
        "raw_environment_included": False,
    }


def _terminal_result(outcome: Any) -> dict[str, Any]:
    # An accepted reference contains only required successes and predeclared
    # skips. Neither platform success nor model output supplies an exit code.
    require(isinstance(outcome, str) and outcome in {"success", "skipped"},
            "required_execution_not_completed", stage="runtime")
    return {
        "result_status": "complete",
        "lifecycle_status": "skipped" if outcome == "skipped" else "completed",
        "outcome": outcome,
        "exit_code": None,
    }


def _job_and_step_records(plan: Mapping[str, Any], job_rows: Sequence[Mapping[str, Any]], subject_run_key: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    by_name: dict[str, Mapping[str, Any]] = {}
    job_ids: set[int] = set()
    for row in job_rows:
        require(isinstance(row, dict), "job_identity_conflict", stage="runtime")
        name = row.get("name")
        identifier = positive_int(row.get("id"), label="runtime_job_id")
        require(isinstance(name, str) and bool(name) and name not in by_name
                and identifier not in job_ids, "job_identity_conflict", stage="runtime")
        by_name[name] = row
        job_ids.add(identifier)
    planned_names = [job.get("display_name") for job in plan.get("jobs", [])]
    require(len(planned_names) == EXPECTED_JOB_COUNT and len(set(planned_names)) == EXPECTED_JOB_COUNT
            and set(planned_names) == set(by_name), "job_extent_mismatch", stage="runtime")
    records: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    workflow_source = _repository_source(plan, SUBJECT_WORKFLOW_PATH)
    for job in plan.get("jobs", []):
        require(isinstance(job, dict), "plan_job_invalid", stage="runtime")
        occurrence = str(job.get("occurrence_id"))
        row = by_name.get(str(job.get("display_name")))
        require(row is not None, "runtime_job_missing", occurrence, stage="runtime")
        expected_run_key = (
            f"GITHUB_RUN_ID={positive_int(row.get('run_id'), label='runtime_job_run_id')}"
            f"|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW={SUBJECT_WORKFLOW_NAME}"
        )
        require(expected_run_key == subject_run_key, "cross_run_context", occurrence, stage="runtime")
        require(type(row.get("run_attempt")) is int and row["run_attempt"] == 1,
                "subject_attempt_mismatch", occurrence, stage="runtime")
        require(row.get("head_sha") == plan["plan_identity"]["source_commit"],
                "subject_source_mismatch", occurrence, stage="runtime")
        require(row.get("status") == "completed", "job_not_terminal", occurrence, stage="runtime")
        job_result = row.get("conclusion")
        require(job_result == job.get("expected_terminal_result"),
                "job_terminal_result_mismatch", occurrence, stage="runtime")
        job_record = {
            "execution_id": occurrence,
            "execution_scope": "subject",
            "execution_kind": "workflow_job",
            "parent_execution_id": None,
            "workflow_name": SUBJECT_WORKFLOW_NAME,
            "job_name": row.get("name"),
            "job_id": positive_int(row.get("id"), label="runtime_job_id"),
            "job_attempt": 1,
            "step_name": None,
            "step_number": None,
            "declared_role": "transition",
            "permitted_mutation_authority": "release_decision",
            "source_identity": workflow_source,
            "command_identity": _unknown_command(),
            "run_binding": {
                "subject_run_key": subject_run_key,
                "execution_run_key": subject_run_key,
                "binding_mode": "current_subject_run",
                "binding_complete": True,
            },
            "timing": _timing(row.get("started_at"), row.get("completed_at")),
            "execution_environment": _execution_environment(),
            "result": _terminal_result(job_result),
            "input_state_ids": [],
            "output_state_ids": [],
            "external_call_ids": [],
            "model_inference_ids": [],
            "resource_measurement_ids": [],
            "capture_status": "complete",
        }
        records.append(job_record)
        index[occurrence] = job_record
        platform_steps = row.get("steps")
        require(isinstance(platform_steps, list), "job_steps_missing", occurrence, stage="runtime")
        expected_steps = [step for step in job.get("steps", []) if isinstance(step, dict) and step.get("expected_runtime_presence") is True]
        if job_result == "skipped":
            require(not platform_steps and not expected_steps,
                    "skipped_job_platform_steps_present", occurrence, stage="runtime")
            continue
        cursor = 0
        for platform in platform_steps:
            require(isinstance(platform, dict), "platform_step_not_object", occurrence, stage="runtime")
            require(platform.get("status") == "completed", "platform_step_not_terminal", occurrence, stage="runtime")
            name = platform.get("name")
            if cursor >= len(expected_steps) or name != expected_steps[cursor].get("name"):
                require(isinstance(name, str) and name in {
                    "Set up job", "Complete job", "Post Checkout", "Post Set up Python"
                }, "unexpected_platform_step", occurrence, stage="runtime")
                require(platform.get("conclusion") in {"success", "skipped"},
                        "platform_lifecycle_result_invalid", occurrence, stage="runtime")
                continue
            expected = expected_steps[cursor]
            require(platform.get("conclusion") == expected.get("expected_terminal_result"),
                    "step_condition_result_mismatch", str(expected.get("occurrence_id")), stage="runtime")
            cursor += 1
            step_occurrence = str(expected.get("occurrence_id"))
            source = expected.get("source") if isinstance(expected.get("source"), dict) else {}
            source_identity = _action_source(source) if source.get("kind") == "github_action" else workflow_source
            record = {
                "execution_id": step_occurrence,
                "execution_scope": "subject",
                "execution_kind": "workflow_step",
                "parent_execution_id": occurrence,
                "workflow_name": SUBJECT_WORKFLOW_NAME,
                "job_name": row.get("name"),
                "job_id": positive_int(row.get("id"), label="runtime_job_id"),
                "job_attempt": 1,
                "step_name": name,
                "step_number": positive_int(expected.get("source_ordinal"), label="source_ordinal"),
                "declared_role": "evidence",
                "permitted_mutation_authority": "release_decision",
                "source_identity": source_identity,
                "command_identity": _step_command(source),
                "run_binding": {
                    "subject_run_key": subject_run_key,
                    "execution_run_key": subject_run_key,
                    "binding_mode": "current_subject_run",
                    "binding_complete": True,
                },
                "timing": _timing(platform.get("started_at"), platform.get("completed_at")),
                "execution_environment": _execution_environment(),
                "result": _terminal_result(platform.get("conclusion")),
                "input_state_ids": [],
                "output_state_ids": [],
                "external_call_ids": [],
                "model_inference_ids": [],
                "resource_measurement_ids": [],
                "capture_status": "complete",
            }
            records.append(record)
            index[step_occurrence] = record
        require(cursor == len(expected_steps), "runtime_step_extent_mismatch", occurrence, stage="runtime")
    require(len(records) == EXPECTED_SUBJECT_EXECUTIONS, "runtime_subject_execution_count_mismatch", str(len(records)), stage="runtime")
    return records, index


def _collector_record(plan: Mapping[str, Any], capture_manifest: Mapping[str, Any], subject_run_key: str) -> dict[str, Any]:
    identity = capture_manifest["capture_identity"]
    collector_key = identity["collector_run_key"]
    source = _repository_source(plan, VERIFIER_PATH)
    return {
        "execution_id": "execution:step5c:collector:post-run-platform-export",
        "execution_scope": "observation_collector",
        "execution_kind": "observer_execution",
        "parent_execution_id": None,
        "workflow_name": REFERENCE_WORKFLOW_NAME,
        "job_name": "verification",
        "job_id": None,
        "job_attempt": 1,
        "step_name": "Construct and verify runtime observation packet",
        "step_number": None,
        "declared_role": "observer",
        "permitted_mutation_authority": "advisory_output",
        "source_identity": source,
        "command_identity": {
            "command_kind": "python_script",
            "display_name": TOOL_ID,
            "command_sha256": None,
            "arguments_sha256": None,
            "raw_command_included": False,
        },
        "run_binding": {
            "subject_run_key": subject_run_key,
            "execution_run_key": collector_key,
            "binding_mode": "post_run_observer",
            "binding_complete": True,
        },
        # Capture timestamps do not time this later reconstruction process.
        "timing": _timing(None, None),
        "execution_environment": _execution_environment(),
        "result": _terminal_result("success"),
        "input_state_ids": [],
        "output_state_ids": [],
        "external_call_ids": [],
        "model_inference_ids": [],
        "resource_measurement_ids": [],
        "capture_status": "complete",
    }


def _generic_state_type(value: str) -> str:
    mapping = {
        "release_evidence": "release_evidence",
        "manifest": "manifest",
        "carrier": "package",
        "expectation": "manifest",
        "subject_input_packet": "manifest",
        "runtime_observation_packet": "manifest",
        "diagnostic": "verifier_report",
        "workflow_source": "workflow_source",
        "policy": "policy",
        "gate_registry": "gate_registry",
        "external_signer_policy": "policy",
        "threshold_policy": "policy",
        "status": "status_artifact",
        "release_decision": "decision_artifact",
        "quality_ledger": "reader_surface",
        "report": "reader_surface",
        "release_authority": "manifest",
        "artifact_binding": "manifest",
        "required_gate_evidence": "release_evidence",
        "evidence_floor": "release_evidence",
        "llamaguard_dataset": "model_request_metadata",
        "llamaguard_raw": "model_response_metadata",
        "llamaguard_manifest": "manifest",
        "llamaguard_summary": "release_evidence",
        "attestation": "attestation",
        "attestation_envelope": "attestation",
        "verifier_report": "verifier_report",
        "candidate_state": "candidate_state",
        "evidence_manifest": "manifest",
        "junit": "reader_surface",
        "sarif": "reader_surface",
        "package": "package",
        "package_inventory": "manifest",
        "package_completeness": "verifier_report",
        "package_verification": "verifier_report",
        "step3f_carrier": "package",
        "step3f_expectation": "manifest",
        "step3f_subject_input": "manifest",
    }
    return mapping.get(value, "other")


# Exact state identities come from the independently checked prelaunch plan.
# A declaration is not evidence that a consumer actually read a state.
SOURCE_STATE_SPECS = {
    "state:step5c:workflow-source": ("workflow_source", SUBJECT_WORKFLOW_PATH),
    "state:step5c:gate-policy": ("policy", POLICY_PATH),
    "state:step5c:gate-registry": ("gate_registry", REGISTRY_PATH),
    "state:step5c:threshold-policy": ("threshold_policy", THRESHOLD_POLICY_PATH),
    "state:step5c:external-signer-policy": ("external_signer_policy", EXTERNAL_SIGNER_POLICY_PATH),
    "state:step5c:llamaguard-dataset": (
        "release_evidence", "PULSE_safe_pack_v0/examples/llamaguard_current_run_cases_v0.jsonl"
    ),
}
TERMINAL_STATE_MEMBERS = {
    "state:step5c:complete-release-grade-reference-package":
        "acquisition/subject/artifacts/complete-release-grade-reference-package.zip",
    "state:step5c:package-completeness-report":
        "acquisition/subject/artifacts/release-grade-package-completeness.zip",
    "state:step5c:package-verification-report":
        "acquisition/subject/artifacts/release-grade-reference-package-verification.zip",
}
# These outputs are checked outside the packet. Hashing the packet or its
# downstream report inside the same packet would introduce a hash cycle.
DERIVED_STATE_MEMBERS = {
    "state:step5c:runtime-observation-packet": RUNTIME_PACKET_MEMBER,
    "state:step5c:runtime-observation-diagnostic": RUNTIME_DIAGNOSTIC_MEMBER,
    "state:step5c:compute-binding-report": BINDING_REPORT_MEMBER,
    "state:step5c:planned-observed-relation": RELATION_MEMBER,
    "state:step5c:folded-non-active-candidate-status": FOLDED_STATUS_MEMBER,
}


def _planned_state_templates(plan: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = plan.get("state_templates")
    require(isinstance(rows, list) and bool(rows), "state_plan_missing", stage="state")
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        require(isinstance(row, dict), "state_template_invalid", stage="state")
        state_id = row.get("state_id")
        require(isinstance(state_id, str) and state_id.startswith("state:step5c:")
                and state_id not in result, "state_template_identity_conflict", stage="state")
        require(type(row.get("required")) is bool and type(row.get("authority_bearing")) is bool,
                "state_template_invalid", state_id, stage="state")
        result[state_id] = row
    return result


def _state_record(
    template: Mapping[str, Any], *, subject_run_key: str, release_candidate: str,
    observed_time: str, raw: bytes | None = None, source: Mapping[str, Any] | None = None,
    producer: str | None = None, media_type: str | None = None,
    schema_identity: str | None = None, path_or_uri: str | None = None,
) -> dict[str, Any]:
    require(not (raw is not None and source is not None), "state_content_source_ambiguous", stage="state")
    if raw is not None:
        sha, size = sha256_bytes(raw), len(raw)
    elif source is not None:
        sha = canonical_sha256(source.get("sha256"), label="state_source_sha256")
        size = source.get("size_bytes")
        require(type(size) is int and size >= 0, "state_source_size_invalid", stage="state")
    else:
        sha, size = None, None
    return {
        "state_id": template["state_id"],
        "state_type": _generic_state_type(template["state_type"]),
        "path_or_uri": path_or_uri if path_or_uri is not None else template["path_or_uri"],
        "content_status": "exact_digest" if sha is not None else "unavailable",
        "sha256": sha, "size_bytes": size, "media_type": media_type,
        "schema_identity": schema_identity, "producer_execution_id": producer,
        "observer_execution_id": "execution:step5c:collector:post-run-platform-export",
        "subject_run_key": subject_run_key, "release_candidate_id": release_candidate,
        "authority_bearing": template["authority_bearing"],
        "mutation_class": template["mutation_class"], "observed_at_utc": observed_time,
        "secret_material_included": False,
    }


def _terminal_artifact_states(
    plan: Mapping[str, Any], capture_manifest: Mapping[str, Any],
    capture_members: Mapping[str, bytes], subject_run_key: str, release_candidate: str,
) -> list[dict[str, Any]]:
    """Observe exact downloaded ZIP bytes, not an unobserved filesystem state.

    Raw platform metadata, the capture binding and actual bytes must agree.
    No source-step producer or downstream-consumption claim is invented from
    the artifact name or the prelaunch declaration alone.
    """
    templates = _planned_state_templates(plan)
    subject = capture_manifest["subject"]
    run_id = positive_int(subject.get("run_id"), label="state_subject_run_id")
    require(type(subject.get("run_attempt")) is int and subject["run_attempt"] == 1
            and subject.get("head_sha") == plan["plan_identity"]["source_commit"],
            "state_artifact_subject_mismatch", stage="state")
    bindings = capture_manifest.get("raw_response_bindings")
    require(isinstance(bindings, list), "state_artifact_pages_missing", stage="state")
    pages = [row for row in bindings if isinstance(row, dict) and row.get("role") == "subject_artifacts_page"]
    maximum = min(256, positive_int(plan["finite_limits"].get("max_artifacts"), label="max_artifacts"))
    require(0 < len(pages) <= (maximum // 100) + 2, "state_artifact_pages_invalid", stage="state")
    metadata: dict[int, Mapping[str, Any]] = {}
    expected_total: int | None = None
    for ordinal, row in enumerate(pages, 1):
        desc = row.get("descriptor")
        require(isinstance(desc, dict), "state_artifact_page_binding_invalid", stage="state")
        member = f"acquisition/subject/artifacts-page-{ordinal:04d}.json"
        raw = capture_members.get(member)
        require(isinstance(raw, bytes) and type(desc.get("size_bytes")) is int
                and desc == descriptor(member, raw), "state_artifact_page_binding_mismatch", member, stage="state")
        page = parse_json_bytes(raw, label="state_artifact_page", canonical=False,
                                maximum=min(16 * 1024 * 1024, plan["finite_limits"]["max_api_json_bytes"]))
        total, values = page.get("total_count"), page.get("artifacts")
        require(type(total) is int and 0 < total <= maximum and isinstance(values, list),
                "state_artifact_page_invalid", stage="state")
        if expected_total is None:
            expected_total = total
        require(total == expected_total and 0 < len(values) <= 100,
                "state_artifact_page_extent_mismatch", stage="state")
        for value in values:
            require(isinstance(value, dict), "state_artifact_row_invalid", stage="state")
            identifier = positive_int(value.get("id"), label="state_artifact_id")
            require(identifier not in metadata, "state_artifact_identity_conflict", stage="state")
            metadata[identifier] = value
    require(len(metadata) == expected_total, "state_artifact_page_extent_mismatch", stage="state")
    rows = capture_manifest.get("artifact_bindings")
    require(isinstance(rows, list), "state_artifact_bindings_missing", stage="state")
    selected = [row for row in rows if isinstance(row, dict) and row.get("artifact_role") == "subject_terminal_artifact"]
    require(len(selected) == len(TERMINAL_STATE_MEMBERS), "state_terminal_artifact_extent_mismatch", stage="state")
    result: list[dict[str, Any]] = []
    used: set[int] = set()
    for state_id, member in TERMINAL_STATE_MEMBERS.items():
        template = templates.get(state_id)
        require(template is not None, "state_terminal_template_missing", state_id, stage="state")
        uri = template["path_or_uri"].replace("{workflow_run_id}", str(run_id))
        require(uri.startswith("artifact://"), "state_terminal_template_invalid", state_id, stage="state")
        name = uri[len("artifact://"):]
        matching = [row for row in selected if row.get("artifact_name") == name]
        require(len(matching) == 1, "state_terminal_artifact_identity_mismatch", state_id, stage="state")
        binding = matching[0]
        identifier = positive_int(binding.get("artifact_id"), label="state_artifact_id")
        require(identifier not in used, "state_artifact_identity_conflict", state_id, stage="state")
        used.add(identifier)
        source = metadata.get(identifier)
        require(source is not None and source.get("name") == name
                and sum(item.get("name") == name for item in metadata.values()) == 1,
                "state_artifact_metadata_mismatch", state_id, stage="state")
        workflow_run = source.get("workflow_run")
        require(binding.get("source_run_kind") == "subject"
                and type(binding.get("source_run_id")) is int and binding["source_run_id"] == run_id
                and type(binding.get("source_run_attempt")) is int and binding["source_run_attempt"] == 1
                and isinstance(workflow_run, dict) and type(workflow_run.get("id")) is int
                and workflow_run["id"] == run_id and workflow_run.get("head_sha") == subject["head_sha"]
                and workflow_run.get("head_branch") == "main",
                "state_artifact_run_binding_mismatch", state_id, stage="state")
        raw = capture_members.get(member)
        require(isinstance(raw, bytes) and binding.get("downloaded_member") == member
                and binding.get("exact_bytes_in_capture") is True,
                "state_artifact_bytes_missing", state_id, stage="state")
        actual_sha = sha256_bytes(raw)
        require(source.get("digest") == "sha256:" + actual_sha
                and binding.get("github_sha256") == binding.get("downloaded_sha256") == actual_sha
                and type(source.get("size_in_bytes")) is int
                and type(binding.get("size_bytes")) is int and type(binding.get("downloaded_size_bytes")) is int
                and source["size_in_bytes"] == binding["size_bytes"] == binding["downloaded_size_bytes"] == len(raw)
                and 0 < len(raw) <= min(805306368, plan["finite_limits"]["max_single_artifact_bytes"]),
                "state_artifact_bytes_binding_mismatch", state_id, stage="state")
        require(source.get("expired") is False and binding.get("expired") is False
                and source.get("created_at") == binding.get("created_utc")
                and source.get("expires_at") == binding.get("expires_utc"),
                "state_artifact_retention_mismatch", state_id, stage="state")
        created = parse_utc(binding["created_utc"], label="state_artifact_created")
        expires = parse_utc(binding["expires_utc"], label="state_artifact_expires")
        observed = capture_manifest["capture_identity"]["capture_completed_utc"]
        require(created < expires and created <= parse_utc(observed, label="state_artifact_observed"),
                "state_artifact_retention_mismatch", state_id, stage="state")
        result.append(_state_record(template, subject_run_key=subject_run_key,
            release_candidate=release_candidate, observed_time=observed, raw=raw,
            path_or_uri=uri, media_type="application/zip"))
    return result


def _project_declared_states(
    plan: Mapping[str, Any], capture_manifest: Mapping[str, Any],
    capture_members: Mapping[str, bytes], observed_states: Sequence[Mapping[str, Any]],
    subject_run_key: str, release_candidate: str,
) -> list[dict[str, Any]]:
    templates = _planned_state_templates(plan)
    states: dict[str, dict[str, Any]] = {}
    for row in [*observed_states, *_terminal_artifact_states(
            plan, capture_manifest, capture_members, subject_run_key, release_candidate)]:
        state_id = row.get("state_id")
        require(state_id in templates and state_id not in states, "state_projection_identity_conflict", stage="state")
        states[state_id] = dict(row)
    # Preserve unfulfilled declarations instead of dropping them from totals.
    # An unavailable state has no invented digest, producer or consumer edge.
    for state_id, template in templates.items():
        if state_id not in states:
            states[state_id] = _state_record(template, subject_run_key=subject_run_key,
                release_candidate=release_candidate,
                observed_time=capture_manifest["capture_identity"]["capture_completed_utc"])
    return sorted(states.values(), key=lambda row: row["state_id"])


def _require_state_projection(
    plan: Mapping[str, Any], packet: Mapping[str, Any],
    capture_manifest: Mapping[str, Any], capture_members: Mapping[str, bytes],
) -> None:
    # Re-derive from preserved inputs, not from claimed coverage or verdicts.
    run_id = positive_int(capture_manifest["subject"].get("run_id"), label="state_subject_run_id")
    key = f"GITHUB_RUN_ID={run_id}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW={SUBJECT_WORKFLOW_NAME}"
    candidate = f"pulse-ci-current-run:{run_id}:1"
    require(packet["subject"].get("subject_run_key") == key
            and packet["subject"].get("release_candidate_id") == candidate,
            "state_subject_binding_mismatch", stage="state")
    _, index = _job_and_step_records(plan, _capture_job_rows(capture_members, capture_manifest), key)
    collector = _collector_record(plan, capture_manifest, key)
    index[collector["execution_id"]] = collector
    states, _ = _build_states_and_inferences(plan, index, capture_manifest,
        capture_members[CAPTURE_PROVIDER_ENVELOPE_MEMBER], key, candidate)
    expected = _project_declared_states(plan, capture_manifest, capture_members, states, key, candidate)
    require(canonical_json_bytes(packet.get("state_observations")) == canonical_json_bytes(expected),
            "state_projection_mismatch", stage="state")
    executions = packet.get("executions")
    require(isinstance(executions, list) and all(isinstance(row, dict) for row in executions),
            "state_execution_binding_mismatch", stage="state")
    execution_ids = [row.get("execution_id") for row in executions]
    require(all(isinstance(identifier, str) for identifier in execution_ids)
            and len(set(execution_ids)) == len(execution_ids)
            and set(execution_ids) == set(index),
            "state_execution_binding_mismatch", stage="state")
    for execution in executions:
        expected_execution = index[execution["execution_id"]]
        for field in ("input_state_ids", "output_state_ids"):
            require(canonical_json_bytes(execution.get(field)) == canonical_json_bytes(expected_execution[field]),
                    "state_execution_binding_mismatch", execution["execution_id"] + ":" + field, stage="state")
    coverage = packet.get("coverage", {})
    status = "complete" if all(row["content_status"] == "exact_digest" for row in expected) else "partial"
    require(type(coverage.get("state_records")) is int and coverage["state_records"] == len(expected)
            and coverage.get("state_digest_capture_status") == status,
            "state_projection_coverage_mismatch", stage="state")


def _require_declared_state_completion(
    plan: Mapping[str, Any], packet: Mapping[str, Any], reconstruction_members: Mapping[str, bytes],
) -> None:
    """Fail before E=complete while required state evidence remains unresolved."""
    templates = _planned_state_templates(plan)
    rows = packet.get("state_observations")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows),
            "state_extent_mismatch", stage="state")
    states = {row.get("state_id"): row for row in rows}
    require(len(states) == len(rows) and set(states) == set(templates), "state_extent_mismatch", stage="state")
    unresolved: list[str] = []
    for state_id, template in templates.items():
        if not template["required"]:
            continue
        if state_id in DERIVED_STATE_MEMBERS:
            # Bind actual downstream output bytes outside the self-referential
            # packet. The enclosing reconstruction inventory checks digests.
            raw = reconstruction_members.get(DERIVED_STATE_MEMBERS[state_id])
            if not isinstance(raw, bytes) or not raw:
                unresolved.append(state_id)
            continue
        state = states[state_id]
        if (state.get("content_status") != "exact_digest"
                or state.get("producer_execution_id") != template["producer_occurrence_id"]):
            unresolved.append(state_id)
    require(not unresolved, "declared_state_evidence_incomplete", ",".join(sorted(unresolved)), stage="state")


def _find_model_records(provider_envelope: bytes) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(provider_envelope), "r") as outer:
            outer_infos = [info for info in outer.infolist() if not info.is_dir()]
            carrier_infos = [info for info in outer_infos if info.filename.endswith("-v0.zip") and not info.filename.endswith("candidate-output-manifest.json")]
            require(len(carrier_infos) == 1, "provider_carrier_not_unique", stage="runtime")
            carrier_raw = outer.read(carrier_infos[0])
        with zipfile.ZipFile(io.BytesIO(carrier_raw), "r") as carrier:
            complete_infos = [info for info in carrier.infolist() if info.filename.endswith("complete-release-grade-reference-package-") is False and "complete-release-grade-reference-package" in info.filename]
            # The exact name has a .zip suffix and is nested under original-github-artifacts.
            complete_infos = [info for info in carrier.infolist() if "complete-release-grade-reference-package" in info.filename and info.filename.endswith(".zip")]
            require(len(complete_infos) == 1, "complete_package_not_unique", stage="runtime")
            complete_raw = carrier.read(complete_infos[0])
        with zipfile.ZipFile(io.BytesIO(complete_raw), "r") as complete:
            raw = complete.read(LLAMAGUARD_RAW_MEMBER)
    except VerificationError:
        raise
    except Exception as exc:
        raise VerificationError("llamaguard_evidence_unavailable", stage="runtime") from exc
    for line in raw.splitlines():
        if not line:
            continue
        row = parse_json_bytes(line + b"\n", label="llamaguard_raw_record", canonical=False, maximum=8 * 1024 * 1024)
        case_id = row.get("case_id")
        require(isinstance(case_id, str) and case_id not in result, "inference_identity_conflict", str(case_id), stage="runtime")
        result[case_id] = row
    require(len(result) == EXPECTED_INFERENCE_COUNT, "inference_extent_mismatch", stage="runtime")
    return result


def _recorded_model_parameters(inference: Mapping[str, Any]) -> dict[str, Any]:
    integer_fields = ("manual_seed", "num_beams", "pad_token_id", "max_new_tokens", "torch_threads")
    for field in integer_fields:
        if field in inference:
            value = inference[field]
            require(type(value) is int and (field == "manual_seed" or value >= 0),
                    "model_parameters_invalid", field, stage="runtime")
    if "do_sample" in inference:
        require(type(inference["do_sample"]) is bool,
                "model_parameters_invalid", "do_sample", stage="runtime")
    for field in ("temperature", "top_p"):
        if field in inference:
            value = inference[field]
            require(type(value) in (int, float) and math.isfinite(value) and value >= 0
                    and (field != "top_p" or value <= 1),
                    "model_parameters_invalid", field, stage="runtime")
    if "device" in inference:
        require(isinstance(inference["device"], str) and bool(inference["device"]),
                "model_parameters_invalid", "device", stage="runtime")
    fields = (*integer_fields, "do_sample", "temperature", "top_p", "device")
    recorded = {field: inference[field] for field in fields if field in inference}
    return {
        "parameters_sha256": sha256_bytes(canonical_json_bytes(recorded)),
        "temperature": inference.get("temperature"),
        "top_p": inference.get("top_p"),
        "max_output_tokens": inference.get("max_new_tokens"),
        "seed": inference.get("manual_seed"),
        # True describes the explicitly recorded non-sampling mode. It does
        # not attest to model internals or cross-platform reproducibility.
        "deterministic_mode": inference.get("do_sample") is False,
    }


def _build_states_and_inferences(
    plan: Mapping[str, Any],
    execution_index: MutableMapping[str, dict[str, Any]],
    capture_manifest: Mapping[str, Any],
    provider_envelope: bytes,
    subject_run_key: str,
    release_candidate: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    collector_id = "execution:step5c:collector:post-run-platform-export"
    observed_time = capture_manifest["capture_identity"]["capture_completed_utc"]
    states: dict[str, dict[str, Any]] = {}

    templates = _planned_state_templates(plan)
    for state_id, (state_type, path) in SOURCE_STATE_SPECS.items():
        template = templates.get(state_id)
        require(template is not None and template.get("state_type") == state_type
                and template.get("path_or_uri") == path
                and template.get("producer_occurrence_id") is None
                and template.get("authority_bearing") is True
                and template.get("mutation_class") == "none"
                and template.get("required") is True
                and template.get("content_requirement") == "exact_digest",
                "source_state_template_mismatch", state_id, stage="state")
        states[state_id] = _state_record(template, source=_source_row(plan, path),
            subject_run_key=subject_run_key, release_candidate=release_candidate,
            observed_time=observed_time)

    raw_rows = _find_model_records(provider_envelope)
    inferences: list[dict[str, Any]] = []
    for template in plan.get("model_inference_templates", []):
        require(isinstance(template, dict), "inference_template_invalid", stage="runtime")
        case_id = str(template.get("case_id"))
        row = raw_rows.get(case_id)
        require(row is not None, "inference_extent_mismatch", case_id, stage="runtime")
        parent_id = str(template.get("parent_occurrence_id"))
        parent = execution_index.get(parent_id)
        require(parent is not None, "inference_parent_missing", parent_id, stage="runtime")
        input_text = row.get("input")
        output_text = row.get("output")
        require(isinstance(input_text, str) and isinstance(output_text, str), "inference_payload_shape_invalid", case_id, stage="runtime")
        input_raw = input_text.encode("utf-8")
        output_raw = output_text.encode("utf-8")
        input_state = str(template.get("input_state_id"))
        output_state = str(template.get("output_state_id"))
        input_template, output_template = templates.get(input_state), templates.get(output_state)
        require(input_template is not None and output_template is not None
                and input_template.get("producer_occurrence_id") is None
                and output_template.get("producer_occurrence_id") == parent_id,
                "inference_state_template_mismatch", case_id, stage="state")
        require(input_state not in states and output_state not in states,
                "inference_state_identity_conflict", case_id, stage="state")
        states[input_state] = _state_record(input_template, raw=input_raw,
            subject_run_key=subject_run_key, release_candidate=release_candidate,
            observed_time=observed_time, media_type="text/plain; charset=utf-8",
            schema_identity="llamaguard_controlled_case_input_v0")
        states[output_state] = _state_record(output_template, raw=output_raw,
            subject_run_key=subject_run_key, release_candidate=release_candidate,
            observed_time=observed_time, producer=parent_id,
            media_type="text/plain; charset=utf-8",
            schema_identity="llamaguard_controlled_case_output_v0")
        inference_data = row.get("inference") if isinstance(row.get("inference"), dict) else {}
        model = row.get("model")
        require(isinstance(model, dict), "model_identity_mismatch", case_id, stage="runtime")
        require(isinstance(model.get("id"), str) and bool(model["id"])
                and model["id"] == template.get("model_id"),
                "model_identity_mismatch", case_id, stage="runtime")
        require(isinstance(model.get("revision"), str)
                and SHA40_RE.fullmatch(model["revision"]) is not None
                and model["revision"] == template.get("model_revision"),
                "model_revision_mismatch", case_id, stage="runtime")
        parameters = _recorded_model_parameters(inference_data)
        prompt_tokens = inference_data.get("prompt_tokens")
        generated_tokens = inference_data.get("generated_tokens")
        require(type(prompt_tokens) is int and type(generated_tokens) is int and prompt_tokens >= 0 and generated_tokens >= 0, "model_usage_mismatch", case_id, stage="runtime")
        total_tokens = prompt_tokens + generated_tokens
        if "total_tokens" in inference_data:
            require(type(inference_data["total_tokens"]) is int
                    and inference_data["total_tokens"] == total_tokens,
                    "model_usage_mismatch", case_id, stage="runtime")
        if parameters["max_output_tokens"] is not None:
            require(generated_tokens <= parameters["max_output_tokens"],
                    "model_usage_mismatch", case_id, stage="runtime")
        inference_id = str(template.get("inference_id"))
        inference = {
            "inference_id": inference_id,
            "parent_execution_id": parent_id,
            "subject_run_key": subject_run_key,
            "model_identity": {
                "provider": "huggingface",
                "model_id": model["id"],
                "model_revision": model["revision"],
                "model_sha256": None,
                "model_content_digest_status": "provider_revision_only",
                "deployment_id_sha256": None,
            },
            "request": {
                "request_metadata_sha256": sha256_bytes(canonical_json_bytes({"case_id": case_id, "input_sha256": sha256_bytes(input_raw)})),
                "input_state_ids": [input_state],
                "raw_prompt_included": False,
            },
            "response": {
                "response_metadata_sha256": sha256_bytes(canonical_json_bytes({"case_id": case_id, "output_sha256": sha256_bytes(output_raw), "label": row.get("llamaguard", {}).get("label")})),
                "output_state_ids": [output_state],
                "output_capture_status": "recorded",
                "raw_output_included": False,
            },
            "parameters": parameters,
            "provider_request_id_sha256": None,
            # The parent step and run-level timestamp do not time a case.
            "timing": _timing(None, None),
            "result": _terminal_result("success"),
            "usage": {
                "input_tokens": prompt_tokens,
                "output_tokens": generated_tokens,
                "total_tokens": prompt_tokens + generated_tokens,
                "usage_status": "complete",
            },
            "resource_measurement_ids": [],
            "capture_status": "complete",
        }
        inferences.append(inference)
        parent["input_state_ids"].append(input_state)
        parent["output_state_ids"].append(output_state)
        parent["model_inference_ids"].append(inference_id)

    for execution in execution_index.values():
        for field in ("input_state_ids", "output_state_ids", "external_call_ids", "model_inference_ids", "resource_measurement_ids"):
            execution[field] = sorted(set(execution[field]))
    return sorted(states.values(), key=lambda row: row["state_id"]), sorted(inferences, key=lambda row: row["inference_id"])


def _external_payload(metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    # A metadata digest binds the explicitly labelled invocation observation,
    # never fabricated request/response bodies or their sizes.
    return {
        "capture_status": "not_recorded" if metadata is None else "metadata_only",
        "metadata_sha256": None if metadata is None else sha256_bytes(canonical_json_bytes(metadata)),
        "body_sha256": None,
        "body_size_bytes": None,
        "state_ids": [],
        "raw_body_included": False,
    }


def _build_external_call_records(
    plan: Mapping[str, Any],
    execution_index: Mapping[str, Mapping[str, Any]],
    subject_run_key: str,
) -> list[dict[str, Any]]:
    """Project the validated plan's subject invocation boundaries, not HTTP traffic.

    This is called only after independent plan/capture checks and job/step
    reconstruction. A GitHub Action step supplies action-invocation metadata.
    A shell block supplies its source descriptor and enclosing platform step,
    not proof that each nested operation executed. Conditional skips are
    explicit skipped records; templates beneath an uninstantiated job produce
    no occurrence. Supervisor/provider operations remain in the outer capture.
    """
    templates = plan.get("external_operation_templates")
    require(isinstance(templates, list) and bool(templates),
            "external_operation_extent_mismatch", stage="runtime")
    by_id: dict[str, Mapping[str, Any]] = {}
    for template in templates:
        require(isinstance(template, dict), "external_operation_template_invalid", stage="runtime")
        identifier = template.get("call_id")
        require(isinstance(identifier, str) and identifier.startswith("call:step5c:")
                and identifier not in by_id,
                "external_operation_identity_conflict", stage="runtime")
        require(isinstance(template.get("owner"), str)
                and template["owner"] in {"subject", "supervisor", "provider"},
                "external_operation_owner_mismatch", identifier, stage="runtime")
        require(template.get("authorization_material_included") is False
                and template.get("cookies_included") is False,
                "privacy_boundary_violation", identifier, stage="runtime")
        by_id[identifier] = template

    # Require agreement in both directions. Removing a template while leaving
    # its step reference, or changing its owner/parent, cannot erase work.
    linked: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for job in plan.get("jobs", []):
        for step in job.get("steps", []):
            identifiers = step.get("external_operation_ids")
            require(isinstance(identifiers, list), "external_operation_extent_mismatch", stage="runtime")
            for identifier in identifiers:
                require(isinstance(identifier, str) and identifier not in linked,
                        "external_operation_identity_conflict", stage="runtime")
                linked[identifier] = (job, step)
    subject_ids = {key for key, value in by_id.items() if value["owner"] == "subject"}
    require(bool(subject_ids) and subject_ids == set(linked),
            "external_operation_extent_mismatch", stage="runtime")

    services = {
        "github_checkout_action": ("GitHub", "checkout"),
        "github_setup_python_action": ("GitHub", "setup-python"),
        "github_artifact_upload": ("GitHub", "artifact-upload"),
        "github_artifact_download": ("GitHub", "artifact-download"),
        "github_artifact_listing": ("GitHub", "artifact-listing"),
        "github_run_metadata_retrieval": ("GitHub", "run-metadata"),
        "github_attestation_action": ("GitHub", "attestation"),
        "system_package_installation": ("system-package-manager", "package-installation"),
        "python_package_installation": ("python-package-manager", "package-installation"),
        "huggingface_model_revision_lookup": ("Hugging Face", "model-revision-lookup"),
        "huggingface_model_file_acquisition": ("Hugging Face", "model-file-acquisition"),
        "other": ("unknown", "declared-external-operation"),
    }
    action_classes = {
        "actions/checkout": "github_checkout_action",
        "actions/setup-python": "github_setup_python_action",
        "actions/upload-artifact": "github_artifact_upload",
        "actions/download-artifact": "github_artifact_download",
    }
    not_recorded_classes = {
        "system_package_installation", "python_package_installation",
        "huggingface_model_file_acquisition",
    }
    shell_classes = {
        "system_package_installation", "python_package_installation",
        "github_artifact_download", "github_artifact_listing",
        "github_run_metadata_retrieval", "huggingface_model_revision_lookup",
        "huggingface_model_file_acquisition",
    }
    records: list[dict[str, Any]] = []
    for identifier in sorted(subject_ids):
        template = by_id[identifier]
        job, step = linked[identifier]
        parent_id = step.get("occurrence_id")
        present = step.get("expected_runtime_presence")
        require(type(present) is bool and template.get("required") is present
                and template.get("parent_occurrence_id") == parent_id,
                "external_operation_parent_mismatch", identifier, stage="runtime")
        operation = template.get("operation_class")
        require(isinstance(operation, str) and operation in services,
                "external_operation_class_mismatch", identifier, stage="runtime")
        source = step.get("source")
        require(isinstance(source, dict) and source.get("kind") in {"github_action", "shell"},
                "external_operation_source_mismatch", identifier, stage="runtime")
        is_action = source["kind"] == "github_action"
        if is_action:
            action_repo = source.get("action_repository")
            require(isinstance(action_repo, str), "external_operation_source_mismatch", identifier, stage="runtime")
            expected_class = ("github_attestation_action" if action_repo.lower().startswith("actions/attest")
                              else action_classes.get(action_repo.lower(), "other"))
            require(operation == expected_class and template.get("capture_requirement") == "metadata_only",
                    "external_operation_class_mismatch", identifier, stage="runtime")
        else:
            expected_capture = "not_recorded" if operation in not_recorded_classes else "metadata_only"
            require(operation in shell_classes and template.get("capture_requirement") == expected_capture,
                    "external_operation_class_mismatch", identifier, stage="runtime")
        parent = execution_index.get(parent_id)
        if not present:
            parent_job = execution_index.get(job.get("occurrence_id"))
            require(parent is None and job.get("expected_terminal_result") == "skipped"
                    and isinstance(parent_job, dict) and parent_job.get("execution_scope") == "subject"
                    and parent_job.get("result", {}).get("outcome") == "skipped",
                    "external_operation_uninstantiated_parent_mismatch", identifier, stage="runtime")
            continue
        require(isinstance(parent, dict) and parent.get("execution_id") == parent_id
                and parent.get("execution_kind") == "workflow_step"
                and parent.get("execution_scope") == "subject"
                and parent.get("parent_execution_id") == job.get("occurrence_id")
                and parent.get("workflow_name") == SUBJECT_WORKFLOW_NAME
                and parent.get("step_name") == step.get("name")
                and type(parent.get("step_number")) is int
                and parent["step_number"] == step.get("source_ordinal")
                and type(parent.get("job_attempt")) is int and parent["job_attempt"] == 1,
                "external_operation_parent_mismatch", identifier, stage="runtime")
        require(parent.get("run_binding", {}).get("binding_complete") is True
                and parent.get("run_binding") == {
            "subject_run_key": subject_run_key, "execution_run_key": subject_run_key,
            "binding_mode": "current_subject_run", "binding_complete": True,
        }, "cross_run_context", identifier, stage="runtime")
        expected_source = _action_source(source) if is_action else _repository_source(plan, SUBJECT_WORKFLOW_PATH)
        require(parent.get("source_identity") == expected_source
                and parent.get("command_identity") == _step_command(source),
                "external_operation_source_mismatch", identifier, stage="runtime")
        outcome = step.get("expected_terminal_result")
        require(parent.get("result") == _terminal_result(outcome),
                "external_operation_result_mismatch", identifier, stage="runtime")

        request_metadata = None
        response_metadata = None
        result = {
            "result_status": "unknown", "lifecycle_status": "unknown",
            "outcome": "unknown", "exit_code": None,
        }
        if outcome == "skipped":
            # A skipped invocation is not a successful call or proof of a
            # request. Neither the source template nor a timestamp creates one.
            result = _terminal_result("skipped")
        elif is_action:
            # These are action invocation/result metadata, not HTTP metadata.
            # The full normalized inputs remain independently derivable from
            # the preserved prelaunch plan and exact platform job/step records.
            request_metadata = {
                "boundary": "github_action_invocation", "call_id": identifier,
                "parent_execution_id": parent_id, "subject_run_key": subject_run_key,
                "source_identity": expected_source,
                "command_identity": parent["command_identity"],
            }
            response_metadata = {
                "boundary": "github_action_platform_result", "call_id": identifier,
                "parent_execution_id": parent_id, "subject_run_key": subject_run_key,
                "job_id": parent["job_id"], "job_attempt": parent["job_attempt"],
                "source_ordinal": parent["step_number"], "step_name": parent["step_name"],
                "platform_result": parent["result"],
            }
            result = _terminal_result("success")
        elif template["capture_requirement"] == "metadata_only":
            request_metadata = {
                "boundary": "declared_shell_operation_not_individual_request",
                "call_id": identifier, "operation_class": operation,
                "parent_execution_id": parent_id, "subject_run_key": subject_run_key,
                "source_identity": expected_source,
                "command_identity": parent["command_identity"],
                "individual_operation_execution_observed": False,
            }
        provider, service = services[operation]
        records.append({
            "call_id": identifier, "parent_execution_id": parent_id,
            "subject_run_key": subject_run_key,
            "service_identity": {
                "provider": provider, "service_name": service,
                "transport": "github_actions" if is_action else "other",
                "endpoint_origin": None, "operation": operation, "api_version": None,
                "identity_status": "partial",
            },
            "request": {
                "method": "OTHER", "payload": _external_payload(request_metadata),
                "authorization_material_included": False, "cookies_included": False,
            },
            "response": {
                "status_code": None, "payload": _external_payload(response_metadata),
                "set_cookie_included": False,
            },
            "provider_request_id_sha256": None,
            # The enclosing step interval is not an internal network-call time.
            "timing": _timing(None, None), "result": result,
            # One declared invocation boundary; provider/internal retry counts
            # are NOT measured and the retry_count resource axis stays absent.
            "retry_index": 0, "resource_measurement_ids": [],
            "capture_status": "partial",
        })
    require(bool(records), "external_operation_extent_mismatch", stage="runtime")
    return records


def _require_external_projection_extent(
    plan: Mapping[str, Any], runtime_packet: Mapping[str, Any],
) -> None:
    """Recheck declared invocation records before recording verification success.

    Generic referential integrity alone cannot detect deletion of a call along
    with its reverse reference and count. Reconstruct the expected records from
    the independently checked plan and bound execution observations instead.
    This does not establish the still-separate state or wider relation extent.
    """
    rows = runtime_packet.get("executions")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows),
            "external_operation_extent_mismatch", stage="verify")
    index: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        identifier = row.get("execution_id")
        require(isinstance(identifier, str) and identifier not in index,
                "external_operation_parent_mismatch", stage="verify")
        index[identifier] = row
    key = runtime_packet.get("subject", {}).get("subject_run_key")
    require(isinstance(key, str) and bool(key), "cross_run_context", stage="verify")
    expected = _build_external_call_records(plan, index, key)
    require(runtime_packet.get("external_calls") == expected,
            "external_operation_extent_mismatch", stage="verify")
    for identifier, row in index.items():
        required_ids = [call["call_id"] for call in expected if call["parent_execution_id"] == identifier]
        require(row.get("external_call_ids") == required_ids,
                "external_operation_parent_mismatch", identifier, stage="verify")
    coverage = runtime_packet.get("coverage", {})
    require(type(coverage.get("external_call_records")) is int
            and coverage["external_call_records"] == len(expected)
            and coverage.get("external_call_capture_status") == "partial",
            "external_operation_coverage_mismatch", stage="verify")


def build_runtime_packet(
    *,
    plan: Mapping[str, Any],
    capture_manifest: Mapping[str, Any],
    capture_members: Mapping[str, bytes],
    record_status: str,
) -> dict[str, Any]:
    require(record_status in {"example", "observed"}, "record_status_invalid", stage="runtime")
    collection_mode = "example" if record_status == "example" else "post_run_platform_export"
    subject = capture_manifest["subject"]
    subject_run_id = positive_int(subject.get("run_id"), label="subject_run_id")
    subject_run_key = f"GITHUB_RUN_ID={subject_run_id}|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW={SUBJECT_WORKFLOW_NAME}"
    release_candidate = f"pulse-ci-current-run:{subject_run_id}:1"
    executions, execution_index = _job_and_step_records(
        plan,
        _capture_job_rows(capture_members, capture_manifest),
        subject_run_key,
    )
    collector = _collector_record(plan, capture_manifest, subject_run_key)
    execution_index[collector["execution_id"]] = collector
    executions.append(collector)
    states, inferences = _build_states_and_inferences(
        plan,
        execution_index,
        capture_manifest,
        capture_members[CAPTURE_PROVIDER_ENVELOPE_MEMBER],
        subject_run_key,
        release_candidate,
    )
    states = _project_declared_states(plan, capture_manifest, capture_members,
        states, subject_run_key, release_candidate)
    external_calls = _build_external_call_records(plan, execution_index, subject_run_key)
    for call in external_calls:
        execution_index[call["parent_execution_id"]]["external_call_ids"].append(call["call_id"])
    for execution in execution_index.values():
        execution["external_call_ids"].sort()
    executions = sorted(execution_index.values(), key=lambda row: row["execution_id"])
    point = capture_manifest["capture_identity"]["capture_completed_utc"]
    workflow_source = _source_row(plan, SUBJECT_WORKFLOW_PATH)
    policy_source = _source_row(plan, POLICY_PATH)
    registry_source = _source_row(plan, REGISTRY_PATH)
    verifier_source = _source_row(plan, VERIFIER_PATH)
    packet = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "packet_type": "pulsemech_compute_runtime_observation_packet",
        "record_status": record_status,
        "producer": {
            "producer_id": "producer:pulsemech-step5c-whole-runtime-observer-v0",
            "producer_name": "PULSEmech Step 5C whole-runtime post-run observer",
            "producer_version": TOOL_VERSION,
            "producer_source": VERIFIER_PATH,
            "producer_source_sha256": verifier_source["sha256"],
            "ci_workflow_or_job_identity": f"{REFERENCE_WORKFLOW_NAME}/verification",
            "collection_mode": collection_mode,
            "producer_execution_id": collector["execution_id"],
        },
        "packet_identity": {
            "packet_id": f"runtime-observation:step5c:{subject_run_id}:1",
            "packet_scope": "example" if record_status == "example" else "subject_run",
            "packet_sequence": 0,
            "canonicalization": "json-sort-keys-utf8-newline",
            "previous_packet_sha256": None,
            "subject_run_key": subject_run_key,
            "packet_created_utc": point,
        },
        "subject": {
            "repository": REPOSITORY,
            "workflow_name": SUBJECT_WORKFLOW_NAME,
            "workflow_run_id": subject_run_id,
            "workflow_run_number": positive_int(subject.get("run_number"), label="subject_run_number"),
            "workflow_run_attempt": 1,
            "source_commit": subject["head_sha"],
            "source_ref": SOURCE_REF,
            "event_name": subject["event"],
            "run_mode": "prod",
            "release_candidate_id": release_candidate,
            "active_policy_sets": (
                ["release_required", "required"] if record_status == "example"
                else ["required", "release_required"]
            ),
            "subject_run_key": subject_run_key,
        },
        "observation_boundary": {
            "target_analysis_level": "runtime_observed",
            "collector_mode": collection_mode,
            "collector_run_key": capture_manifest["capture_identity"]["collector_run_key"],
            "collector_execution_id": collector["execution_id"],
            "subject_run_key": subject_run_key,
            "observer_in_subject_totals": False,
            "subject_artifacts_mutated": False,
            "capture_started_utc": capture_manifest["capture_identity"]["capture_started_utc"],
            "capture_completed_utc": point,
        },
        "authority_inputs": {
            "workflow": {
                "role": "workflow",
                "path": SUBJECT_WORKFLOW_PATH,
                "source_commit": subject["head_sha"],
                "sha256": workflow_source["sha256"],
            },
            "policy": {
                "role": "policy",
                "path": POLICY_PATH,
                "source_commit": subject["head_sha"],
                "sha256": policy_source["sha256"],
            },
            "gate_registry": {
                "role": "gate_registry",
                "path": REGISTRY_PATH,
                "source_commit": subject["head_sha"],
                "sha256": registry_source["sha256"],
            },
        },
        "timing_basis": {
            "timestamps_utc": True,
            "primary_clock_source": "mixed",
            "timestamp_resolution_ms": 1000.0,
            "duration_derivation": "derived_from_recorded_timestamps",
            "cross_source_clock_status": "not_verified",
            "duration_values_estimated": False,
        },
        # Step 5C's opaque-fixture declarations remain in its outer carrier.
        # The unchanged generic packet has a narrower, closed privacy shape.
        "privacy_boundary": {
            key: PRIVACY_BOUNDARY[key]
            for key in (
                "raw_environment_included", "secret_values_included",
                "authorization_headers_included", "cookies_included",
                "request_bodies_included", "response_bodies_included",
                "raw_prompt_text_included", "raw_model_output_included",
                "redaction_applied", "redaction_rules_sha256",
            )
        },
        "executions": executions,
        "state_observations": states,
        "external_calls": external_calls,
        "model_inferences": inferences,
        "resource_measurements": [],
        "coverage": {
            "coverage_status": "partial",
            "expected_job_count": EXPECTED_JOB_COUNT,
            "observed_job_count": EXPECTED_JOB_COUNT,
            "expected_step_count": EXPECTED_STEP_COUNT,
            "observed_step_count": EXPECTED_STEP_COUNT,
            "execution_records": EXPECTED_TOTAL_EXECUTIONS,
            "state_records": len(states),
            "external_call_records": len(external_calls),
            "model_inference_records": EXPECTED_INFERENCE_COUNT,
            "resource_measurement_records": 0,
            "external_call_capture_status": "partial",
            "model_inference_capture_status": "complete",
            "state_digest_capture_status": (
                "complete" if all(row["content_status"] == "exact_digest" for row in states)
                else "partial"
            ),
            "missing_execution_ids": [],
            "unobserved_reasons": sorted(set(GENERIC_UNOBSERVED_REASONS) | (
                {"post_decision_state_unavailable"}
                if any(row["content_status"] == "unavailable" for row in states) else set()
            )),
            "resource_axes_observed": [],
            "resource_axes_unavailable": RESOURCE_AXES,
        },
        "errors": [],
        "ok": True,
    }
    return packet


def _safe_env(home: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
    }


def run_process(command: Sequence[str], *, cwd: Path, timeout: int = PROCESS_TIMEOUT_SECONDS) -> ProcessOutput:
    try:
        process = subprocess.run(
            list(command),
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            env=_safe_env(cwd),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VerificationError("subprocess_execution_failed", str(command[0]), stage="reconstruct") from exc
    require(len(process.stdout) <= MAX_PROCESS_STDOUT and len(process.stderr) <= MAX_PROCESS_STDERR, "subprocess_output_too_large", str(command[0]), stage="reconstruct")
    return ProcessOutput(process.returncode, process.stdout, process.stderr)


def require_success(process: ProcessOutput, *, label: str) -> bytes:
    require(process.returncode == 0, "subprocess_failed", f"{label}:{process.returncode}:{process.stderr.decode('utf-8', errors='replace')[:2000]}", stage="reconstruct")
    return process.stdout


def clone_at_revision(source: Path, destination: Path, revision: str) -> None:
    require(not destination.exists(), "clone_destination_exists", str(destination), stage="reconstruct")
    result = run_process(
        [
            "/usr/bin/git",
            "clone",
            "--quiet",
            "--no-hardlinks",
            "--no-checkout",
            str(source),
            str(destination),
        ],
        cwd=source,
        timeout=300,
    )
    require_success(result, label="git_clone")
    checkout = run_process(
        [
            "/usr/bin/git",
            "-C",
            str(destination),
            "-c",
            "advice.detachedHead=false",
            "checkout",
            "--quiet",
            revision,
        ],
        cwd=source,
        timeout=300,
    )
    require_success(checkout, label="git_checkout")
    head = git(destination, ["rev-parse", "HEAD"], max_bytes=4096).decode("ascii").strip()
    require(head == revision, "clone_revision_mismatch", str(destination), stage="reconstruct")


def _find_unique(root: Path, name: str) -> Path:
    matches = [path for path in root.rglob(name) if path.is_file() and not path.is_symlink()]
    require(len(matches) == 1, "derived_output_not_unique", f"{name}:{len(matches)}", stage="reconstruct")
    return matches[0]


def _provider_artifact_binding(capture_manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    rows = capture_manifest.get("artifact_bindings")
    require(isinstance(rows, list), "artifact_bindings_missing", stage="capture")
    matches = [row for row in rows if isinstance(row, dict) and row.get("artifact_role") == "step3f_candidate_envelope"]
    require(len(matches) == 1, "provider_artifact_binding_not_unique", stage="capture")
    return matches[0]


def _write_read_only(path: Path, raw: bytes) -> None:
    require(not path.exists(), "temporary_output_exists", str(path), stage="reconstruct")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    path.chmod(0o444)


def _normalize_diagnostic(raw: bytes, *, label: str) -> bytes:
    value = parse_json_bytes(raw, label=label, canonical=False)
    return canonical_json_bytes(value)


def _materializer_candidate_values(report_raw: bytes, status_raw: bytes) -> dict[str, bool]:
    report = parse_json_bytes(report_raw, label="candidate_materializer_report", canonical=False)
    status = parse_json_bytes(status_raw, label="folded_candidate_status", canonical=False)
    candidates = report.get("candidate_gates")
    if not isinstance(candidates, dict):
        gates = status.get("gates")
        candidates = gates if isinstance(gates, dict) else {}
    values: dict[str, bool] = {}
    for key in (
        "compute_transition_path_complete",
        "compute_transition_authority_binding_ok",
        "compute_transition_unbound_mutation_absent",
    ):
        value = candidates.get(key)
        require(type(value) is bool, "candidate_value_missing", key, stage="reconstruct")
        values[key] = value
    values["candidate_all_true"] = all(values.values())
    return values


def _candidate_envelope_to_file(capture_members: Mapping[str, bytes], path: Path) -> None:
    _write_read_only(path, capture_members[CAPTURE_PROVIDER_ENVELOPE_MEMBER])


def _load_step3f_intake(
    *,
    control_root: Path,
    capture_manifest: Mapping[str, Any],
    envelope_path: Path,
    output_directory: Path,
    source_commit: str,
) -> None:
    provider = capture_manifest["provider"]
    artifact = _provider_artifact_binding(capture_manifest)
    command = [
        sys.executable,
        "-I",
        "-B",
        str(control_root / STEP3F_LOADER_PATH),
        "--artifact-envelope",
        str(envelope_path),
        "--repository",
        REPOSITORY,
        "--provider-workflow-name",
        PROVIDER_WORKFLOW_NAME,
        "--provider-workflow-path",
        PROVIDER_WORKFLOW_PATH,
        "--provider-workflow-run-id",
        str(provider["run_id"]),
        "--provider-workflow-run-number",
        str(provider["run_number"]),
        "--provider-workflow-run-attempt",
        "1",
        "--provider-workflow-event",
        "workflow_dispatch",
        "--provider-workflow-head-branch",
        "main",
        "--provider-workflow-revision",
        source_commit,
        "--provider-workflow-status",
        "completed",
        "--provider-workflow-conclusion",
        "success",
        "--provider-workflow-updated-utc",
        provider["updated_at"],
        "--provider-artifact-id",
        str(artifact["artifact_id"]),
        "--provider-artifact-name",
        str(artifact["artifact_name"]),
        "--provider-artifact-created-utc",
        str(artifact["created_utc"]),
        "--provider-artifact-expires-utc",
        str(artifact["expires_utc"]),
        "--provider-artifact-expired",
        "false",
        "--provider-artifact-sha256",
        str(artifact["github_sha256"]),
        "--provider-artifact-size-bytes",
        str(artifact["size_bytes"]),
        "--producer-run-key",
        capture_manifest["capture_identity"]["collector_run_key"] + "|PHASE=step3f-intake",
        "--ci-workflow-or-job-identity",
        f"{REFERENCE_WORKFLOW_NAME}/verification/step3f-intake",
        "--control-plane-root",
        str(control_root),
        "--control-plane-revision",
        source_commit,
        "--output-directory",
        str(output_directory),
    ]
    require_success(run_process(command, cwd=control_root), label="step3f_bundle_loader")


def _build_baseline_proof(
    *,
    control_root: Path,
    subject_root: Path,
    intake_directory: Path,
    output_directory: Path,
    source_commit: str,
    capture_manifest: Mapping[str, Any],
) -> None:
    subject_id = capture_manifest["subject"]["run_id"]
    command = [
        sys.executable,
        "-I",
        "-B",
        str(control_root / STEP3G_PROOF_BUILDER_PATH),
        "--intake-directory",
        str(intake_directory),
        "--subject-root",
        str(subject_root),
        "--subject-repository",
        REPOSITORY,
        "--subject-revision",
        source_commit,
        "--control-plane-root",
        str(control_root),
        "--control-plane-repository",
        REPOSITORY,
        "--control-plane-revision",
        source_commit,
        "--analysis-run-key",
        f"analysis:step5c:{subject_id}:1:artifact-baseline",
        "--producer-run-key",
        capture_manifest["capture_identity"]["collector_run_key"] + "|PHASE=artifact-baseline",
        "--ci-workflow-or-job-identity",
        f"{REFERENCE_WORKFLOW_NAME}/verification/artifact-baseline",
        "--output-directory",
        str(output_directory),
    ]
    require_success(run_process(command, cwd=control_root), label="step3g_baseline_proof")


def _run_existing_pipeline(
    *,
    control_root: Path,
    intake_directory: Path,
    baseline_proof: Path,
    runtime_packet_path: Path,
    output_root: Path,
    source_commit: str,
    subject_run_id: int,
) -> dict[str, bytes]:
    subject_packet = _find_unique(intake_directory, "subject-input-packet.json")
    carrier_candidates = [path for path in intake_directory.iterdir() if path.is_file() and path.name.endswith("-v0.zip")]
    require(len(carrier_candidates) == 1, "step3f_carrier_not_unique", stage="reconstruct")
    carrier = carrier_candidates[0]
    plan_path = _find_unique(baseline_proof, "current-run-plan.json")
    baseline_relation = _find_unique(baseline_proof, "planned-observed-relation.json")
    baseline_status = _find_unique(baseline_proof, "folded-candidate-status.json")
    baseline_relation_doc = parse_json_bytes(baseline_relation.read_bytes(), label="baseline_relation", canonical=False)
    expectations = baseline_relation_doc.get("expectations")
    require(isinstance(expectations, dict), "baseline_expectations_missing", stage="reconstruct")
    expectations_path = output_root / "expectations.json"
    expectations_path.write_bytes(canonical_json_bytes(expectations))

    runtime_diag = require_success(
        run_process(
            [
                sys.executable,
                "-I",
                "-B",
                str(control_root / RUNTIME_VALIDATOR_PATH),
                "--schema",
                str(control_root / RUNTIME_SCHEMA_PATH),
                "--packet",
                str(runtime_packet_path),
            ],
            cwd=control_root,
        ),
        label="runtime_packet_validator",
    )
    runtime_diag = _normalize_diagnostic(runtime_diag, label="runtime_packet_diagnostic")

    report_raw = require_success(
        run_process(
            [
                sys.executable,
                "-I",
                "-B",
                str(control_root / BINDING_BRIDGE_PATH),
                "--packet",
                str(subject_packet),
                "--carrier",
                str(carrier),
                "--repository-root",
                str(control_root),
                "--analysis-run-key",
                f"analysis:step5c:{subject_run_id}:1:runtime",
                "--runtime-packet",
                str(runtime_packet_path),
            ],
            cwd=control_root,
        ),
        label="binding_bridge",
    )
    report_path = output_root / BINDING_REPORT_MEMBER
    report_path.write_bytes(report_raw)

    report_diag = require_success(
        run_process(
            [
                sys.executable,
                "-I",
                "-B",
                str(control_root / BINDING_REPORT_VALIDATOR_PATH),
                "--schema",
                str(control_root / BINDING_REPORT_SCHEMA_PATH),
                "--report",
                str(report_path),
                "--subject-input",
                str(subject_packet),
                "--carrier",
                str(carrier),
                "--repository-root",
                str(control_root),
                "--runtime-packet",
                str(runtime_packet_path),
            ],
            cwd=control_root,
        ),
        label="binding_report_validator",
    )
    report_diag = _normalize_diagnostic(report_diag, label="binding_report_diagnostic")

    relation_raw = require_success(
        run_process(
            [
                sys.executable,
                "-I",
                "-B",
                str(control_root / RELATION_BUILDER_PATH),
                "--plan",
                str(plan_path),
                "--compute-report",
                str(report_path),
                "--expectations",
                str(expectations_path),
                "--runtime-packet",
                str(runtime_packet_path),
                "--subject-input",
                str(subject_packet),
                "--carrier",
                str(carrier),
                "--repository-root",
                str(control_root),
                "--tool-source-revision",
                source_commit,
            ],
            cwd=control_root,
        ),
        label="relation_builder",
    )
    relation_path = output_root / RELATION_MEMBER
    relation_path.write_bytes(relation_raw)

    relation_diag = require_success(
        run_process(
            [
                sys.executable,
                "-I",
                "-B",
                str(control_root / RELATION_VALIDATOR_PATH),
                "--relation",
                str(relation_path),
                "--plan",
                str(plan_path),
                "--compute-report",
                str(report_path),
                "--expectations",
                str(expectations_path),
                "--runtime-packet",
                str(runtime_packet_path),
                "--subject-input",
                str(subject_packet),
                "--carrier",
                str(carrier),
                "--repository-root",
                str(control_root),
            ],
            cwd=control_root,
        ),
        label="relation_validator",
    )
    relation_diag = _normalize_diagnostic(relation_diag, label="relation_diagnostic")

    folded_path = output_root / FOLDED_STATUS_MEMBER
    materializer_raw = require_success(
        run_process(
            [
                sys.executable,
                "-I",
                "-B",
                str(control_root / CANDIDATE_MATERIALIZER_PATH),
                "--status",
                str(baseline_status),
                "--relation",
                str(relation_path),
                "--output",
                str(folded_path),
                "--plan",
                str(plan_path),
                "--compute-report",
                str(report_path),
                "--expectations",
                str(expectations_path),
                "--runtime-packet",
                str(runtime_packet_path),
                "--subject-input",
                str(subject_packet),
                "--carrier",
                str(carrier),
                "--repository-root",
                str(control_root),
            ],
            cwd=control_root,
        ),
        label="candidate_materializer",
    )
    require(folded_path.is_file(), "folded_candidate_status_missing", stage="reconstruct")
    return {
        RUNTIME_PACKET_MEMBER: runtime_packet_path.read_bytes(),
        RUNTIME_DIAGNOSTIC_MEMBER: runtime_diag,
        BINDING_REPORT_MEMBER: report_raw,
        BINDING_DIAGNOSTIC_MEMBER: report_diag,
        RELATION_MEMBER: relation_raw,
        RELATION_DIAGNOSTIC_MEMBER: relation_diag,
        MATERIALIZER_REPORT_MEMBER: _normalize_diagnostic(materializer_raw, label="candidate_materializer_report"),
        FOLDED_STATUS_MEMBER: folded_path.read_bytes(),
    }


def _reconstruction_inventory(
    *,
    outputs: Mapping[str, bytes],
    source_commit: str,
    capture_manifest: Mapping[str, Any],
    candidate_values: Mapping[str, bool],
) -> bytes:
    rows = [descriptor(name, raw) for name, raw in sorted(outputs.items())]
    value = {
        "schema_version": "pulsemech_compute_whole_runtime_observation_reconstruction_inventory_v0",
        "record_status": capture_manifest["record_status"],
        "repository": REPOSITORY,
        "source_commit": source_commit,
        "capture_id": capture_manifest["capture_identity"]["capture_id"],
        "subject_run_id": capture_manifest["subject"]["run_id"],
        "subject_run_attempt": 1,
        "manifest_scope": "all_reconstruction_members_except_this_inventory",
        "member_count": len(rows),
        "members": rows,
        "candidate_values": dict(candidate_values),
        "authority_boundary": AUTHORITY_BOUNDARY,
        "reconstruction_boundary": {
            "dispatched_workflow": False,
            "repeated_model_inference": False,
            "used_current_time": False,
            "used_randomness": False,
            "ambient_environment_dependency": False,
        },
        "errors": [],
        "ok": True,
    }
    return canonical_json_bytes(value)


def reconstruct(
    *,
    repository_root: Path,
    source_commit: str,
    prepared_path: Path,
    capture_path: Path,
    expected_context_path: Path,
    expected_plan_digest_path: Path,
    output_path: Path,
    record_status: str,
    work_root: Path,
) -> dict[str, Any]:
    root = validate_repository(repository_root, source_commit)
    expected_digest_raw = expected_plan_digest_path.read_bytes()
    require(len(expected_digest_raw) == 65 and expected_digest_raw.endswith(b"\n"), "expected_plan_digest_file_invalid", stage="context")
    expected_digest = canonical_sha256(expected_digest_raw[:-1].decode("ascii"), label="expected_plan_sha256")
    expected_context_raw = expected_context_path.read_bytes()
    expected_context = _expected_context(expected_context_raw, source_commit=source_commit, expected_plan_sha256=expected_digest, record_status=record_status)
    schema_raw, _oid, _exec = git_blob(root, source_commit, SCHEMA_PATH)
    schema = parse_source_schema(schema_raw)
    plan, _prepared_members, _prepared_raw = read_prepared(prepared_path, source_commit=source_commit, expected_digest=expected_digest, record_status=record_status, schema=schema)
    verify_source_inventory(root, source_commit, plan)
    capture_manifest, capture_members, _capture_raw = read_capture(
        capture_path,
        schema=schema,
        plan=plan,
        expected_plan_sha256=expected_digest,
        expected_context_raw=expected_context_raw,
        record_status=record_status,
        source_commit=source_commit,
    )
    require(capture_manifest["capture_identity"]["reference_run_id"] == expected_context["reference_run_id"], "reference_run_binding_mismatch", stage="context")

    stable = Path(os.path.abspath(os.fspath(work_root)))
    require(stable == FIXED_RECONSTRUCTION_ROOT, "reconstruction_root_not_canonical", str(stable), stage="reconstruct")
    require(not stable.exists(), "reconstruction_root_exists", str(stable), stage="reconstruct")
    stable.mkdir(mode=0o700, parents=True)
    try:
        control_root = stable / "control-plane"
        subject_root = stable / "subject"
        clone_at_revision(root, control_root, source_commit)
        clone_at_revision(root, subject_root, source_commit)
        envelope_path = stable / "step3f-candidate-envelope.zip"
        _candidate_envelope_to_file(capture_members, envelope_path)
        intake = stable / "intake"
        _load_step3f_intake(
            control_root=control_root,
            capture_manifest=capture_manifest,
            envelope_path=envelope_path,
            output_directory=intake,
            source_commit=source_commit,
        )
        baseline = stable / "baseline-proof"
        _build_baseline_proof(
            control_root=control_root,
            subject_root=subject_root,
            intake_directory=intake,
            output_directory=baseline,
            source_commit=source_commit,
            capture_manifest=capture_manifest,
        )
        packet = build_runtime_packet(
            plan=plan,
            capture_manifest=capture_manifest,
            capture_members=capture_members,
            record_status=record_status,
        )
        runtime_packet_path = stable / RUNTIME_PACKET_MEMBER
        runtime_packet_path.write_bytes(canonical_json_bytes(packet))
        output_root = stable / "derived"
        output_root.mkdir()
        outputs = _run_existing_pipeline(
            control_root=control_root,
            intake_directory=intake,
            baseline_proof=baseline,
            runtime_packet_path=runtime_packet_path,
            output_root=output_root,
            source_commit=source_commit,
            subject_run_id=int(capture_manifest["subject"]["run_id"]),
        )
        candidate_values = _materializer_candidate_values(
            outputs[MATERIALIZER_REPORT_MEMBER],
            outputs[FOLDED_STATUS_MEMBER],
        )
        inventory_raw = _reconstruction_inventory(
            outputs=outputs,
            source_commit=source_commit,
            capture_manifest=capture_manifest,
            candidate_values=candidate_values,
        )
        members = dict(outputs)
        members[RECONSTRUCTION_INVENTORY_MEMBER] = inventory_raw
        raw = deterministic_zip_bytes(
            members,
            maximum_members=MAX_RECONSTRUCTION_MEMBERS,
            maximum_bytes=MAX_RECONSTRUCTION_BYTES,
        )
        digest, size = publish_bytes(output_path, raw)
        return {
            "tool": TOOL_ID,
            "version": TOOL_VERSION,
            "mode": "reconstruct",
            "record_status": record_status,
            "ok": True,
            "output": str(Path(output_path).absolute()),
            "output_sha256": digest,
            "output_size_bytes": size,
            "inventory_sha256": sha256_bytes(inventory_raw),
            "inventory_size_bytes": len(inventory_raw),
            "subject_run_id": capture_manifest["subject"]["run_id"],
            "provider_run_id": capture_manifest["provider"]["run_id"],
            "candidate_values": candidate_values,
            "authority_boundary": AUTHORITY_BOUNDARY,
            "errors": [],
        }
    finally:
        if stable.exists():
            shutil.rmtree(stable)


def _read_reconstruction(path: Path) -> tuple[dict[str, bytes], dict[str, Any], bytes]:
    raw = path.read_bytes()
    members = read_canonical_zip_bytes(
        raw,
        label="reconstruction",
        maximum_members=MAX_RECONSTRUCTION_MEMBERS,
        maximum_bytes=MAX_RECONSTRUCTION_BYTES,
    )
    required = {
        RUNTIME_PACKET_MEMBER,
        RUNTIME_DIAGNOSTIC_MEMBER,
        BINDING_REPORT_MEMBER,
        BINDING_DIAGNOSTIC_MEMBER,
        RELATION_MEMBER,
        RELATION_DIAGNOSTIC_MEMBER,
        MATERIALIZER_REPORT_MEMBER,
        FOLDED_STATUS_MEMBER,
        RECONSTRUCTION_INVENTORY_MEMBER,
    }
    require(set(members) == required, "reconstruction_member_set_mismatch", stage="verify")
    inventory = parse_json_bytes(members[RECONSTRUCTION_INVENTORY_MEMBER], label="reconstruction_inventory")
    rows = inventory.get("members")
    require(isinstance(rows, list) and inventory.get("member_count") == 8, "reconstruction_inventory_count_mismatch", stage="verify")
    declared = {row.get("member"): row for row in rows if isinstance(row, dict)}
    require(set(declared) == required - {RECONSTRUCTION_INVENTORY_MEMBER}, "reconstruction_inventory_mismatch", stage="verify")
    for name, row in declared.items():
        require(row.get("sha256") == sha256_bytes(members[name]) and row.get("size_bytes") == len(members[name]), "reconstruction_member_identity_mismatch", str(name), stage="verify")
    require(inventory.get("authority_boundary") == AUTHORITY_BOUNDARY and inventory.get("ok") is True, "reconstruction_authority_boundary_mismatch", stage="verify")
    return members, inventory, raw


def _derived_output_rows(members: Mapping[str, bytes]) -> list[dict[str, Any]]:
    roles = {
        RUNTIME_PACKET_MEMBER: "runtime_observation_packet",
        RUNTIME_DIAGNOSTIC_MEMBER: "runtime_packet_diagnostic",
        BINDING_REPORT_MEMBER: "compute_binding_report",
        BINDING_DIAGNOSTIC_MEMBER: "binding_report_diagnostic",
        RELATION_MEMBER: "planned_observed_relation",
        RELATION_DIAGNOSTIC_MEMBER: "relation_diagnostic",
        MATERIALIZER_REPORT_MEMBER: "candidate_materializer_report",
        FOLDED_STATUS_MEMBER: "folded_candidate_status",
        RECONSTRUCTION_INVENTORY_MEMBER: "reconstruction_inventory",
    }
    return [
        {"role": roles[name], "descriptor": descriptor(name, members[name])}
        for name in sorted(roles, key=lambda item: roles[item])
    ]


def _verification_checks(
    *,
    prepared_raw: bytes,
    capture_raw: bytes,
    expected_context_raw: bytes,
    expected_digest_raw: bytes,
    recon_raw: bytes,
    runtime_packet: Mapping[str, Any],
) -> list[dict[str, Any]]:
    names = [
        "authority_boundary_preserved",
        "capture_carrier_canonical",
        "capture_inventory_closed",
        "capture_plan_binding_exact",
        "collector_excluded_from_subject_totals",
        "expected_context_bound",
        "expected_plan_digest_bound",
        "external_operation_extent_preserved",
        "declared_state_extent_complete",
        "generic_runtime_packet_validated",
        "inference_extent_complete",
        "job_extent_complete",
        "no_resource_measurement_introduced",
        "plan_independently_checked",
        "prepared_carrier_canonical",
        "provider_dispatch_receipt_bound",
        "provider_subject_binding_exact",
        "reconstruction_byte_identity",
        "reconstruction_inventory_closed",
        "relation_remains_non_authoritative",
        "runtime_coverage_remains_partial",
        "source_inventory_exact",
        "step_extent_complete",
        "subject_dispatch_receipt_bound",
        "subject_source_and_attempt_bound",
        "two_process_reconstruction_complete",
    ]
    details = {
        "prepared_carrier_canonical": sha256_bytes(prepared_raw),
        "capture_carrier_canonical": sha256_bytes(capture_raw),
        "expected_context_bound": sha256_bytes(expected_context_raw),
        "expected_plan_digest_bound": sha256_bytes(expected_digest_raw),
        "reconstruction_byte_identity": sha256_bytes(recon_raw),
        "job_extent_complete": str(runtime_packet["coverage"]["observed_job_count"]),
        "step_extent_complete": str(runtime_packet["coverage"]["observed_step_count"]),
        "inference_extent_complete": str(runtime_packet["coverage"]["model_inference_records"]),
        "external_operation_extent_preserved": str(runtime_packet["coverage"]["external_call_records"]),
        "declared_state_extent_complete": str(runtime_packet["coverage"]["state_records"]),
    }
    return [
        {"check_id": name, "passed": True, "detail": details.get(name)}
        for name in sorted(names)
    ]


def _verification_record(
    *,
    root: Path,
    source_commit: str,
    prepared_path: Path,
    prepared_raw: bytes,
    capture_path: Path,
    capture_raw: bytes,
    expected_context_path: Path,
    expected_context_raw: bytes,
    expected_digest_path: Path,
    expected_digest_raw: bytes,
    capture_manifest: Mapping[str, Any],
    reconstruction_members: Mapping[str, bytes],
    reconstruction_raw: bytes,
    reconstructions: Sequence[ReconstructionResult],
    schema: Mapping[str, Any],
    record_status: str,
) -> bytes:
    packet = parse_json_bytes(reconstruction_members[RUNTIME_PACKET_MEMBER], label="runtime_packet")
    prepared_members = read_canonical_zip_bytes(
        prepared_raw, label="prepared", maximum_members=MAX_PREPARED_MEMBERS,
        maximum_bytes=MAX_PREPARED_BYTES,
    )
    plan = parse_json_bytes(prepared_members[PREPARED_PLAN_MEMBER], label="prelaunch_plan")
    _require_external_projection_extent(plan, packet)
    capture_members = read_canonical_zip_bytes(
        capture_raw, label="state_capture", maximum_members=MAX_CAPTURE_MEMBERS,
        maximum_bytes=MAX_CAPTURE_BYTES,
    )
    require(capture_members.get(CAPTURE_MANIFEST_MEMBER) == canonical_json_bytes(capture_manifest),
            "state_capture_manifest_mismatch", stage="state")
    _require_state_projection(plan, packet, capture_manifest, capture_members)
    _require_declared_state_completion(plan, packet, reconstruction_members)
    candidate_values = _materializer_candidate_values(
        reconstruction_members[MATERIALIZER_REPORT_MEMBER],
        reconstruction_members[FOLDED_STATUS_MEMBER],
    )
    verifier_source = _source_row(plan, VERIFIER_PATH)
    identity = capture_manifest["capture_identity"]
    point = identity["capture_completed_utc"]
    record = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "verification_record",
        "record_status": record_status,
        "verification_identity": {
            "verification_id": f"step5c-verification:{capture_manifest['subject']['run_id']}:1",
            "repository": REPOSITORY,
            "source_commit": source_commit,
            "tool": {
                "tool_id": TOOL_ID,
                "version": TOOL_VERSION,
                "source_path": VERIFIER_PATH,
                "source_revision": source_commit,
                "source_sha256": verifier_source["sha256"],
            },
            "reference_run_id": identity["reference_run_id"],
            "reference_run_attempt": 1,
            "subject_run_id": capture_manifest["subject"]["run_id"],
            "subject_run_attempt": 1,
            "provider_run_id": capture_manifest["provider"]["run_id"],
            "provider_run_attempt": 1,
            "verification_started_utc": point,
            "verification_completed_utc": point,
        },
        "input_bindings": {
            "prepared_carrier": file_descriptor("prepared.zip", prepared_path),
            "capture_carrier": file_descriptor("capture.zip", capture_path),
            "expected_context": file_descriptor("expected_context.json", expected_context_path),
            "expected_plan_digest": file_descriptor("expected_plan.sha256", expected_digest_path),
        },
        "subject": capture_manifest["subject"],
        "provider": capture_manifest["provider"],
        "checks": _verification_checks(
            prepared_raw=prepared_raw,
            capture_raw=capture_raw,
            expected_context_raw=expected_context_raw,
            expected_digest_raw=expected_digest_raw,
            recon_raw=reconstruction_raw,
            runtime_packet=packet,
        ),
        "result": {
            "I": "complete",
            "E": "complete",
            "R": "partial",
            "comparison_complete": False,
            "M": "unavailable",
            "generic_runtime_coverage": "partial",
            "expected_job_count": EXPECTED_JOB_COUNT,
            "observed_job_count": EXPECTED_JOB_COUNT,
            "expected_instantiated_step_count": EXPECTED_STEP_COUNT,
            "observed_declared_step_count": EXPECTED_STEP_COUNT,
            "expected_inference_count": EXPECTED_INFERENCE_COUNT,
            "observed_inference_count": EXPECTED_INFERENCE_COUNT,
            "missing_job_occurrence_ids": [],
            "missing_step_occurrence_ids": [],
            "missing_inference_ids": [],
            "resource_axes_observed": [],
            "resource_axes_unavailable": RESOURCE_AXES,
            "unobserved_reasons": UNOBSERVED_REASONS,
            "authority_binding_complete": False,
            "decision_closure_complete": False,
            "candidate_values": candidate_values,
        },
        "runtime_packet_result": {
            "packet": descriptor(RUNTIME_PACKET_MEMBER, reconstruction_members[RUNTIME_PACKET_MEMBER]),
            "diagnostic": descriptor(RUNTIME_DIAGNOSTIC_MEMBER, reconstruction_members[RUNTIME_DIAGNOSTIC_MEMBER]),
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "record_status": record_status,
            "coverage_status": "partial",
            "packet_sequence": 0,
            "previous_packet_sha256": None,
            "subject_execution_records": EXPECTED_SUBJECT_EXECUTIONS,
            "collector_execution_records": EXPECTED_COLLECTOR_EXECUTIONS,
            "total_execution_records": EXPECTED_TOTAL_EXECUTIONS,
            "model_inference_records": EXPECTED_INFERENCE_COUNT,
            "resource_measurement_records": 0,
        },
        "derived_outputs": _derived_output_rows(reconstruction_members),
        "reconstructions": [
            {
                "ordinal": index + 1,
                "process_run_key": item.process_run_key,
                "process_id": item.process_id,
                "exit_code": 0,
                "completed": True,
                "output_zip": file_descriptor(f"reconstruction-{index + 1}.zip", item.output),
                "inventory_member": RECONSTRUCTION_INVENTORY_MEMBER,
                "inventory_sha256": item.inventory_sha256,
                "inventory_size_bytes": item.inventory_size_bytes,
                "dispatched_workflow": False,
                "repeated_model_inference": False,
                "used_current_time": False,
                "used_randomness": False,
                "ambient_environment_dependency": False,
            }
            for index, item in enumerate(reconstructions)
        ],
        "reconstruction_comparison": {
            "reconstruction_count": 2,
            "byte_identical": True,
            "member_inventory_identical": True,
            "common_sha256": sha256_bytes(reconstruction_raw),
            "common_size_bytes": len(reconstruction_raw),
        },
        "privacy_boundary": PRIVACY_BOUNDARY,
        "trust_boundary": TRUST_BOUNDARY,
        "authority_boundary": AUTHORITY_BOUNDARY,
        "errors": [],
        "ok": True,
    }
    validate_schema(schema, record, label="verification_record")
    return canonical_json_bytes(record)


def _spawn_reconstruction(
    *,
    ordinal: int,
    root: Path,
    source_commit: str,
    prepared: Path,
    capture: Path,
    expected_context: Path,
    expected_digest: Path,
    output: Path,
    record_status: str,
) -> ReconstructionResult:
    command = [
        sys.executable,
        "-I",
        "-B",
        str(root / VERIFIER_PATH),
        "reconstruct",
        "--repository-root",
        str(root),
        "--source-commit",
        source_commit,
        "--prepared",
        str(prepared),
        "--capture",
        str(capture),
        "--expected-context",
        str(expected_context),
        "--expected-plan-digest",
        str(expected_digest),
        "--output",
        str(output),
        "--record-status",
        record_status,
        "--work-root",
        str(FIXED_RECONSTRUCTION_ROOT),
    ]
    process = subprocess.Popen(
        command,
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_safe_env(root),
    )
    stdout, stderr = process.communicate(timeout=PROCESS_TIMEOUT_SECONDS * 2)
    require(process.returncode == 0, "reconstruction_process_failed", f"{ordinal}:{stderr.decode('utf-8', errors='replace')[:2000]}", stage="verify")
    result = parse_json_bytes(stdout, label=f"reconstruction_{ordinal}_diagnostic", canonical=False)
    require(result.get("ok") is True and result.get("output_sha256") == sha256_file(output)[0], "reconstruction_diagnostic_mismatch", str(ordinal), stage="verify")
    return ReconstructionResult(
        output=output,
        sha256=result["output_sha256"],
        size_bytes=result["output_size_bytes"],
        inventory_sha256=result["inventory_sha256"],
        inventory_size_bytes=result["inventory_size_bytes"],
        process_id=positive_int(process.pid, label="reconstruction_process_id"),
        process_run_key=f"PROCESS=step5c-reconstruction-{ordinal}|REFERENCE_RUN_ID={result.get('subject_run_id')}|ATTEMPT=1",
    )


def run_reference(
    *,
    repository_root: Path,
    source_commit: str,
    prepared_path: Path,
    capture_path: Path,
    expected_context_path: Path,
    expected_plan_digest_path: Path,
    output_directory: Path,
    record_status: str,
) -> dict[str, Any]:
    root = validate_repository(repository_root, source_commit)
    destination = Path(os.path.abspath(os.fspath(output_directory)))
    require(not destination.exists() and not destination.is_symlink(), "output_already_exists", str(destination), stage="output")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        recon1_path = staging / "reconstruction-1.zip"
        recon2_path = staging / "reconstruction-2.zip"
        reconstruction1 = _spawn_reconstruction(
            ordinal=1,
            root=root,
            source_commit=source_commit,
            prepared=prepared_path,
            capture=capture_path,
            expected_context=expected_context_path,
            expected_digest=expected_plan_digest_path,
            output=recon1_path,
            record_status=record_status,
        )
        reconstruction2 = _spawn_reconstruction(
            ordinal=2,
            root=root,
            source_commit=source_commit,
            prepared=prepared_path,
            capture=capture_path,
            expected_context=expected_context_path,
            expected_digest=expected_plan_digest_path,
            output=recon2_path,
            record_status=record_status,
        )
        members1, inventory1, recon1_raw = _read_reconstruction(recon1_path)
        members2, inventory2, recon2_raw = _read_reconstruction(recon2_path)
        require(recon1_raw == recon2_raw, "reconstruction_mismatch", stage="verify")
        require(inventory1 == inventory2, "reconstruction_inventory_mismatch", stage="verify")

        expected_digest_raw = expected_plan_digest_path.read_bytes()
        expected_digest = canonical_sha256(expected_digest_raw[:-1].decode("ascii"), label="expected_plan_sha256")
        expected_context_raw = expected_context_path.read_bytes()
        schema_raw, _oid, _exec = git_blob(root, source_commit, SCHEMA_PATH)
        schema = parse_source_schema(schema_raw)
        plan, _prepared_members, prepared_raw = read_prepared(
            prepared_path,
            source_commit=source_commit,
            expected_digest=expected_digest,
            record_status=record_status,
            schema=schema,
        )
        capture_manifest, _capture_members, capture_raw = read_capture(
            capture_path,
            schema=schema,
            plan=plan,
            expected_plan_sha256=expected_digest,
            expected_context_raw=expected_context_raw,
            record_status=record_status,
            source_commit=source_commit,
        )
        verification_raw = _verification_record(
            root=root,
            source_commit=source_commit,
            prepared_path=prepared_path,
            prepared_raw=prepared_raw,
            capture_path=capture_path,
            capture_raw=capture_raw,
            expected_context_path=expected_context_path,
            expected_context_raw=expected_context_raw,
            expected_digest_path=expected_plan_digest_path,
            expected_digest_raw=expected_digest_raw,
            capture_manifest=capture_manifest,
            reconstruction_members=members1,
            reconstruction_raw=recon1_raw,
            reconstructions=[reconstruction1, reconstruction2],
            schema=schema,
            record_status=record_status,
        )
        verification_path = staging / VERIFICATION_RECORD_MEMBER
        verification_path.write_bytes(verification_raw)
        verification_path.chmod(0o444)

        payloads: dict[str, Path | bytes] = {
            "prepared.zip": prepared_path,
            "capture.zip": capture_path,
            "expected_context.json": expected_context_path,
            "expected_plan.sha256": expected_plan_digest_path,
            "reconstruction-1.zip": recon1_path,
            "reconstruction-2.zip": recon2_path,
            VERIFICATION_RECORD_MEMBER: verification_path,
        }
        sums_rows: list[str] = []
        for name, source in sorted(payloads.items()):
            if isinstance(source, bytes):
                digest = sha256_bytes(source)
            else:
                digest = sha256_file(source)[0]
            sums_rows.append(f"{digest}  {name}\n")
        payloads["SHA256SUMS"] = "".join(sums_rows).encode("ascii")
        capsule_staged = staging / REFERENCE_CAPSULE_NAME
        capsule_sha, capsule_size = publish_zip_from_files(capsule_staged, payloads)

        # Publish one closed directory by no-replacement rename.
        for path in staging.iterdir():
            if path.is_file():
                path.chmod(0o444)
        staging.chmod(0o555)
        _rename_noreplace(staging, destination)
        staging = Path("/")  # prevents cleanup of the published directory
        return {
            "tool": TOOL_ID,
            "version": TOOL_VERSION,
            "mode": "run-reference",
            "record_status": record_status,
            "ok": True,
            "output_directory": str(destination),
            "reference_capsule": str(destination / REFERENCE_CAPSULE_NAME),
            "reference_capsule_sha256": capsule_sha,
            "reference_capsule_size_bytes": capsule_size,
            "verification_record_sha256": sha256_bytes(verification_raw),
            "verification_record_size_bytes": len(verification_raw),
            "reconstruction_sha256": sha256_bytes(recon1_raw),
            "reconstruction_size_bytes": len(recon1_raw),
            "subject_run_id": capture_manifest["subject"]["run_id"],
            "provider_run_id": capture_manifest["provider"]["run_id"],
            "authority_boundary": AUTHORITY_BOUNDARY,
            "errors": [],
        }
    finally:
        if staging != Path("/") and staging.exists():
            shutil.rmtree(staging)


def failure(error: VerificationError, *, exit_code: int = 2) -> dict[str, Any]:
    return {
        "tool": TOOL_ID,
        "version": TOOL_VERSION,
        "record_status": "rejected",
        "ok": False,
        "stage": error.stage,
        "error_code": error.code,
        "detail": error.detail,
        "authority_effect": "none",
        "same_run_release_authority_eligible": False,
        "active_gate_eligible": False,
        "exit_code": exit_code,
    }


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--record-status", choices=("example", "observed"), default="observed")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Independent Step 5C verification and deterministic reconstruction."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare")
    _common(prepare)
    prepare.add_argument("--plan", required=True)
    prepare.add_argument("--plan-diagnostic", required=True)
    prepare.add_argument("--expected-plan-sha256", required=True)
    prepare.add_argument("--output", required=True)

    reconstruct_parser = sub.add_parser("reconstruct")
    _common(reconstruct_parser)
    reconstruct_parser.add_argument("--prepared", required=True)
    reconstruct_parser.add_argument("--capture", required=True)
    reconstruct_parser.add_argument("--expected-context", required=True)
    reconstruct_parser.add_argument("--expected-plan-digest", required=True)
    reconstruct_parser.add_argument("--output", required=True)
    reconstruct_parser.add_argument("--work-root", default=str(FIXED_RECONSTRUCTION_ROOT))

    run = sub.add_parser("run-reference")
    _common(run)
    run.add_argument("--prepared", required=True)
    run.add_argument("--capture", required=True)
    run.add_argument("--expected-context", required=True)
    run.add_argument("--expected-plan-digest", required=True)
    run.add_argument("--output-directory", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_carrier(
                repository_root=Path(args.repository_root),
                source_commit=str(args.source_commit),
                plan_path=Path(args.plan),
                diagnostic_path=Path(args.plan_diagnostic),
                expected_plan_sha256=str(args.expected_plan_sha256),
                output=Path(args.output),
                record_status=str(args.record_status),
            )
        elif args.command == "reconstruct":
            result = reconstruct(
                repository_root=Path(args.repository_root),
                source_commit=str(args.source_commit),
                prepared_path=Path(args.prepared),
                capture_path=Path(args.capture),
                expected_context_path=Path(args.expected_context),
                expected_plan_digest_path=Path(args.expected_plan_digest),
                output_path=Path(args.output),
                record_status=str(args.record_status),
                work_root=Path(args.work_root),
            )
        else:
            result = run_reference(
                repository_root=Path(args.repository_root),
                source_commit=str(args.source_commit),
                prepared_path=Path(args.prepared),
                capture_path=Path(args.capture),
                expected_context_path=Path(args.expected_context),
                expected_plan_digest_path=Path(args.expected_plan_digest),
                output_directory=Path(args.output_directory),
                record_status=str(args.record_status),
            )
    except VerificationError as exc:
        sys.stderr.buffer.write(canonical_json_bytes(failure(exc)))
        return 2
    except Exception as exc:  # fail closed without exposing arbitrary bytes
        error = VerificationError("unexpected_verifier_failure", type(exc).__name__, stage="internal")
        sys.stderr.buffer.write(canonical_json_bytes(failure(error)))
        return 2
    sys.stdout.buffer.write(canonical_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
