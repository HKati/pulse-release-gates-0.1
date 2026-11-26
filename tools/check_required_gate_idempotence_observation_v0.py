#!/usr/bin/env python3
"""Replay the selected finite operator's recorded input/output relationships.

This offline adapter never imports or executes acquired source bytes. It checks
caller-selected bytes, projects a truthful standalone runtime packet, and reuses
the existing compute consumption and planned/observed relation mechanisms.
Acceptance is recorded-relation integrity, not authenticated execution, an
idempotence verdict, runtime closure, or release authority.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import zipfile
import zlib
from datetime import datetime
from typing import Any

import check_required_gate_suite_contract_v0 as safe
import pulsemech_compute_binding_analyzer_core_v0 as core
import build_pulsemech_compute_planned_observed_relation_v0 as relation
import pulsemech_compute_standalone_runtime_v0 as standalone

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = "schemas/required_gate_idempotence_observation_v0.schema.json"
SCHEMA_SHA256 = "9ff17460c8d2648ddfdf10b9431540bed46aba4e12b5e0b7836303342cc4bd04"
PROFILE = "standalone_operator_v0"
PROTOCOL_ID = "epf_snapshot_idempotence_v0"
REPOSITORY = "HKati/pulse-release-gates-0.1"
BASELINE = "97ab500bb9936c27632e1f40ab891d2442476786"
CONFIGURATION = {"max_depth": 2, "max_items": 3,
                 "allowed_prefixes": ["metrics"], "deny_keys": ["metrics.pii", "metrics.secret"]}
PROTOCOL_PINS = {
    "protocol_proposal_v0.json": (49965, "6df92cb2f5fb139606fe8ace66b9ee2bb2dd6b8db82e41c97ab8094425cdc225"),
    "inputs_v0.json": (6900, "dd70d0fe1fee4fd5ad9ba960647828160f595627281ed47af88098c6f09af66b"),
    "observation_mapping_v0.json": (19666, "304fe5bfb0351645f8aab83d3a64f1ff3639a20d6441364a267076fe7c4d60ff"),
}
ARCHIVE_LIMIT = 4 * 1024 * 1024
TOTAL_LIMIT = 2 * 1024 * 1024
MEMBER_LIMIT = 512 * 1024
MAX_MEMBERS = 123
INVENTORY = "capture/member_inventory.json"
HEX = re.compile(r"[0-9a-f]{64}\Z")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
PATH = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\Z")
ID = re.compile(r"[A-Za-z0-9._:@+-]+\Z")
BOUNDARY = {
    "execution_ready": False, "execution_authorized": False,
    "property_semantics_verified": False, "metric_pass": None,
    "production_gate_eligible": False, "authority_effect": "none",
    "anchor_authentication": "not_established", "runtime_closure_verified": False,
    "actual_reference_claimed": False,
}


class VerificationError(ValueError):
    """Stable public code; never echo untrusted payloads or filesystem paths."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def need(condition: bool, code: str) -> None:
    if not condition:
        raise VerificationError(code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise VerificationError("canonicalization_failed") from exc


def parse(raw: bytes) -> dict[str, Any]:
    need(type(raw) is bytes and len(raw) <= MEMBER_LIMIT, "document_size_limit")
    try:
        return safe._json(raw)
    except safe.ContractError as exc:
        raise VerificationError(exc.code) from exc


def validate_shape(value: dict[str, Any], definition: str) -> None:
    # All references in this schema are local. Use B1's strict integer typing,
    # duplicate/overflow guards and closed-schema validator without changing B1.
    try:
        schema_bytes = safe._read_regular(ROOT / SCHEMA_PATH)
        need(sha(schema_bytes) == SCHEMA_SHA256, "schema_source_mismatch")
        schema = safe._json(schema_bytes)
        safe._validate_schema(value, schema, definition + "_schema_invalid", definition)
    except safe.ContractError as exc:
        raise VerificationError(exc.code) from exc


def path_ok(value: Any) -> bool:
    return (isinstance(value, str) and 0 < len(value) <= 400
            and PATH.fullmatch(value) is not None
            and all(part not in {".", ".."} for part in value.split("/")))


def bound(raw: bytes, descriptor: dict[str, Any], code: str) -> None:
    need(type(descriptor.get("size_bytes")) is int
         and descriptor["size_bytes"] == len(raw) and descriptor.get("sha256") == sha(raw), code)


def snapshot_domain(value: dict[str, Any]) -> None:
    """Check the selected output domain without calculating the property.

    Boolean values are not numeric leaves even though bool subclasses int in
    Python. Strict parsing has already rejected nonfinite/overflowed numbers.
    """
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            pending.extend(item.values())
        else:
            need(type(item) in (int, float), "snapshot_domain_invalid")


def _zip_layout(raw: bytes, entries: list[zipfile.ZipInfo]) -> None:
    """Close the physical carrier, not just its central-directory inventory.

    This small bounded profile uses one ordinary seekable non-ZIP64 archive.
    Prefixes, trailers, unindexed local entries, data descriptors, extra fields
    and bytes after a deflate end marker are outside its selected format.
    """
    need(len(raw) >= 22, "carrier_layout_invalid")
    end = struct.unpack_from("<4s4H2LH", raw, len(raw) - 22)
    signature, disk, directory_disk, disk_count, count, directory_size, directory_start, comment = end
    need(signature == b"PK\x05\x06" and disk == directory_disk == comment == 0
         and disk_count == count == len(entries)
         and directory_start + directory_size == len(raw) - 22, "carrier_layout_invalid")
    cursor = directory_start
    for entry in entries:
        need(cursor + 46 <= len(raw) - 22, "carrier_layout_invalid")
        header = struct.unpack_from("<4s6H3L5H2L", raw, cursor)
        name_size, extra_size, comment_size, entry_disk = header[10:14]
        end_name = cursor + 46 + name_size
        need(header[0] == b"PK\x01\x02" and extra_size == comment_size == entry_disk == 0
             and header[-1] == entry.header_offset and end_name <= len(raw) - 22
             and raw[cursor + 46:end_name] == entry.filename.encode("ascii"), "carrier_layout_invalid")
        cursor = end_name
    need(cursor == len(raw) - 22, "carrier_layout_invalid")
    cursor = 0
    for entry in sorted(entries, key=lambda value: value.header_offset):
        need(entry.header_offset == cursor and cursor + 30 <= directory_start, "carrier_layout_invalid")
        header = struct.unpack_from("<4s5H3L2H", raw, cursor)
        signature, version, flags, compression, _time, _date, crc, packed_size, unpacked_size, name_size, extra_size = header
        begin = cursor + 30 + name_size
        finish = begin + packed_size
        need(signature == b"PK\x03\x04" and version <= 20 and flags in {0, 2048}
             and flags == entry.flag_bits and compression == entry.compress_type and extra_size == 0
             and crc == entry.CRC and packed_size == entry.compress_size and unpacked_size == entry.file_size
             and finish <= directory_start and raw[cursor + 30:begin] == entry.filename.encode("ascii"),
             "carrier_layout_invalid")
        if compression == zipfile.ZIP_STORED:
            need(packed_size == unpacked_size, "carrier_layout_invalid")
        elif compression == zipfile.ZIP_DEFLATED:
            inflater = zlib.decompressobj(-15)
            data = inflater.decompress(raw[begin:finish], unpacked_size + 1)
            need(inflater.eof and not inflater.unused_data and not inflater.unconsumed_tail
                 and len(data) == unpacked_size, "carrier_deflate_extent_invalid")
        cursor = finish
    need(cursor == directory_start, "carrier_layout_invalid")


def read_archive(raw: bytes) -> dict[str, bytes]:
    need(type(raw) is bytes and 0 < len(raw) <= ARCHIVE_LIMIT, "carrier_size_limit")
    members: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            need(0 < len(entries) <= MAX_MEMBERS, "carrier_member_count_limit")
            need(not archive.comment, "carrier_archive_comment_forbidden")
            total = 0
            for entry in entries:
                name = entry.filename
                need(path_ok(name) and entry.orig_filename == name and not entry.is_dir(),
                     "carrier_member_path_invalid")
                need(name not in members, "carrier_duplicate_member")
                kind = stat.S_IFMT(entry.external_attr >> 16)
                need(kind in {0, stat.S_IFREG}, "carrier_member_type_invalid")
                need(entry.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                     and not (entry.flag_bits & (1 | 64)), "carrier_encoding_unsupported")
                need(not entry.comment and not entry.extra, "carrier_member_extra_forbidden")
                need(0 <= entry.file_size <= MEMBER_LIMIT, "carrier_member_size_limit")
                total += entry.file_size
                need(total <= TOTAL_LIMIT, "carrier_total_size_limit")
                with archive.open(entry) as stream:
                    data = stream.read(entry.file_size + 1)
                need(len(data) == entry.file_size, "carrier_member_size_mismatch")
                members[name] = data
            _zip_layout(raw, entries)
    except VerificationError:
        raise
    except (ValueError, OSError, RuntimeError, zipfile.BadZipFile, NotImplementedError,
            struct.error, zlib.error, UnicodeError) as exc:
        raise VerificationError("carrier_invalid") from exc
    return members


def verify_inventory(members: dict[str, bytes], expected: set[str]) -> None:
    need(set(members) == expected, "carrier_inventory_mismatch")
    inventory = parse(members[INVENTORY])
    validate_shape(inventory, "inventory")
    rows = inventory["members"]
    names = [item["member"] for item in rows]
    need(len(names) == len(set(names)), "inventory_duplicate_member")
    need(set(names) == expected - {INVENTORY}, "inventory_coverage_mismatch")
    for item in rows:
        bound(members[item["member"]], item, "inventory_byte_mismatch")


def _git_blob(root: Path, revision: str, path: str, expected_size: int) -> bytes:
    """Read a selected commit blob; no hooks, replacement objects, or execution."""
    need(path_ok(path) and bool(SHA40.fullmatch(revision)), "source_locator_invalid")
    try:
        safe._Reader(root)  # Refuse symlink components before Git traverses root.
    except safe.ContractError as exc:
        raise VerificationError("repository_root_unsafe") from exc
    # Missing objects in a partial clone must stay missing. Repository-local
    # promisor/remote configuration must not turn a blob read into a fetch or
    # execute a remote/credential helper. Transport denial is also effective on
    # Git versions that do not recognize GIT_NO_LAZY_FETCH.
    env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_REPLACE_OBJECTS": "1",
           "GIT_NO_LAZY_FETCH": "1", "GIT_ALLOW_PROTOCOL": "",
           "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/false",
           "GIT_SSH_COMMAND": "/bin/false"}

    def git(arguments: list[str], limit: int) -> bytes:
        try:
            result = subprocess.run(["/usr/bin/git", "--no-replace-objects",
                                     "-c", "protocol.allow=never", "-c", "credential.helper=",
                                     "-c", "core.fsmonitor=false", "-c", "gc.auto=0",
                                     "-C", str(root), *arguments],
                                    env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise VerificationError("source_git_unavailable") from exc
        need(result.returncode == 0 and len(result.stdout) <= limit, "source_git_unavailable")
        return result.stdout

    need(git(["cat-file", "-t", revision], 32) == b"commit\n", "source_revision_not_commit")
    entry = git(["ls-tree", "-z", revision, "--", path], 1024)
    need(entry.startswith((b"100644 blob ", b"100755 blob ")) and entry.count(b"\0") == 1
         and entry.endswith(b"\t" + path.encode() + b"\0"), "source_git_type_invalid")
    locator = revision + ":" + path
    need(git(["cat-file", "-s", locator], 32).strip() == str(expected_size).encode(),
         "source_git_size_mismatch")
    return git(["cat-file", "blob", locator], MEMBER_LIMIT)


def invocation_binding(selection: dict[str, Any], application_id: str,
                       input_descriptor: dict[str, Any]) -> tuple[str, str]:
    worker = next(item for item in selection["sources"] if item["role"] == "worker")
    arguments = {"application_id": application_id,
                 "configuration_sha256": sha(canonical_bytes(selection["configuration"])),
                 "input_state_id": input_descriptor["state_id"],
                 "input_sha256": input_descriptor["sha256"],
                 "input_size_bytes": input_descriptor["size_bytes"]}
    args_sha = sha(canonical_bytes(arguments))
    command = {"worker_path": worker["path"], "worker_revision": worker["source_revision"],
               "worker_sha256": worker["sha256"],
               "executable_sha256": selection["environment"]["executable_sha256"],
               "arguments_sha256": args_sha}
    return args_sha, sha(canonical_bytes(command))


def _selection(selection: dict[str, Any], members: dict[str, bytes], *,
               repository_root: Path | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    validate_shape(selection, "selection")
    need(canonical_bytes(selection["configuration"]) == canonical_bytes(CONFIGURATION), "configuration_mismatch")
    for name, (size, digest) in PROTOCOL_PINS.items():
        raw = members.get("selection/" + name)
        need(raw is not None and len(raw) == size and sha(raw) == digest, "protocol_selection_mismatch")
    protocol = parse(members["selection/protocol_proposal_v0.json"])
    catalog = parse(members["selection/inputs_v0.json"])
    mapping = parse(members["selection/observation_mapping_v0.json"])
    cases = catalog["cases"]
    roster = mapping["planned_applications"]
    need(sorted(selection["applications"], key=lambda x: x["case_id"]) == roster,
         "selected_application_roster_mismatch")
    sources = selection["sources"]
    paths = [item["path"] for item in sources]
    need(len(paths) == len(set(paths)) and all(path_ok(path) for path in paths), "source_path_invalid")
    need(all(item["member"] == "sources/" + item["path"] for item in sources), "source_member_mismatch")
    for role in ("worker", "collector"):
        selected = [item for item in sources if item["role"] == role]
        need(len(selected) == 1, "source_role_mismatch")
        need(selected[0]["source_revision"] == selection["source_commit"]
             and selected[0]["size_bytes"] > 0, "implementation_revision_mismatch")
    fixed_sources = protocol["source_inventory"][:4]
    source_map = {item["path"]: item for item in sources}
    for original in fixed_sources:
        item = source_map.get(original["path"], {})
        need(all(item.get(key) == original[key] for key in ("sha256", "size_bytes"))
             and item.get("source_revision") == original["source_commit"]
             and item.get("role") == ("operator" if original["role"] == "selected_operator_module"
                                      else "operator_dependency"), "operator_source_mismatch")
    fixed_paths = {item["path"] for item in fixed_sources}
    need(all(item["path"] in fixed_paths for item in sources
             if item["role"] in {"operator", "operator_dependency"}), "operator_source_extra")
    if selection["record_status"] == "observed":
        need(repository_root is not None, "observed_repository_required")
    admitted = []
    for item in sources:
        need(item["member"] in members, "source_member_missing")
        data = members[item["member"]]
        bound(data, item, "source_byte_mismatch")
        if selection["record_status"] == "observed":
            need(_git_blob(Path(repository_root), item["source_revision"], item["path"], item["size_bytes"])
                 == data, "source_git_blob_mismatch")
        admitted.append({key: item[key] for key in ("path", "source_revision", "sha256", "size_bytes")}
                        | {"data": data})
    return admitted, {item["case_id"]: item for item in cases}


def _utc(value: str) -> datetime:
    try:
        need(value.endswith("Z"), "timestamp_invalid")
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except (ValueError, TypeError) as exc:
        if isinstance(exc, VerificationError):
            raise
        raise VerificationError("timestamp_invalid") from exc


def _interval(row: dict[str, Any], *, maximum_ns: int) -> tuple[datetime, datetime]:
    started, completed = _utc(row["started_utc"]), _utc(row["completed_utc"])
    delta = row["completed_monotonic_ns"] - row["started_monotonic_ns"]
    need(started <= completed and 0 <= delta <= maximum_ns, "capture_time_invalid")
    need((completed - started).total_seconds() <= maximum_ns / 1e9, "capture_time_limit")
    return started, completed


def _contexts(selection, context, receipts, selection_sha):
    validate_shape(context, "context")
    validate_shape(receipts, "receipts")
    for key in ("record_status", "acquisition_id", "acquisition_attempt", "repository", "source_commit", "environment"):
        need(context[key] == selection[key], "capture_context_mismatch")
    need(context["selection_sha256"] == selection_sha
         and receipts["selection_sha256"] == selection_sha
         and receipts["record_status"] == selection["record_status"], "capture_selection_mismatch")
    _interval(context, maximum_ns=180_000_000_000)
    collector_source = next(item for item in selection["sources"] if item["role"] == "collector")
    collector = context["collector"]
    need(collector["source_path"] == collector_source["path"]
         and collector["source_revision"] == collector_source["source_revision"], "collector_source_mismatch")
    need(collector["exit_code"] == 0, "collector_incomplete")


def _expected_members(selection, cases):
    result = {"selection/" + name for name in PROTOCOL_PINS}
    result.update({"selection/pre_acquisition_selection.json", "capture/context.json",
                   "capture/application_receipts.json", INVENTORY})
    result.update(item["member"] for item in selection["sources"])
    for cid in cases:
        result.add("inputs/" + cid + ".json")
        for phase in ("first", "second"):
            app = cid + "." + phase
            result.update({"snapshots/" + app + ".json", "metadata/" + app + ".json",
                           "diagnostics/" + app + ".stderr"})
    return result


def _applications(selection, context, receipts, cases, members):
    rows = receipts["applications"]
    app_ids = [row["application_id"] for row in rows]
    expected = {cid + "." + phase for cid in cases for phase in ("first", "second")}
    need(len(app_ids) == len(set(app_ids)) and set(app_ids) == expected, "application_roster_mismatch")
    execution_ids = [row["execution_id"] for row in rows] + [context["collector"]["execution_id"]]
    process_ids = [row["process_id"] for row in rows] + [context["collector"]["process_id"]]
    need(len(set(execution_ids)) == 25, "execution_identity_reused")
    need(len(set(process_ids)) == 25, "process_identity_reused")
    worker = next(item for item in selection["sources"] if item["role"] == "worker")
    configuration_sha = sha(canonical_bytes(selection["configuration"]))
    environment_sha = sha(canonical_bytes(selection["environment"]))
    applications = {row["application_id"]: row for row in rows}
    declared_states = set()
    for cid, case in sorted(cases.items()):
        original = members["inputs/" + cid + ".json"]
        need(original == case["input_utf8"].encode("utf-8") and len(original) <= 1024,
             "initial_input_mismatch")
        parse(original)
        first, second = applications[cid + ".first"], applications[cid + ".second"]
        first_input = first["input"]
        need(first_input["member"] == "inputs/" + cid + ".json", "initial_input_member_mismatch")
        # Identity is essential even when all three payloads happen to be equal.
        need({key: second["input"][key] for key in ("state_id", "member", "sha256", "size_bytes")}
             == first["snapshot"], "derived_input_mismatch")
        need(first["completed_monotonic_ns"] <= second["started_monotonic_ns"]
             and _utc(first["completed_utc"]) <= _utc(second["started_utc"]), "composition_order_invalid")
        state_ids = [first_input["state_id"]]
        for phase, row in (("first", first), ("second", second)):
            app = cid + "." + phase
            need(row["case_id"] == cid and row["phase"] == phase, "application_assignment_mismatch")
            need(row["source_path"] == worker["path"] and row["source_revision"] == worker["source_revision"],
                 "worker_source_mismatch")
            need(row["configuration_sha256"] == configuration_sha
                 and row["environment_sha256"] == environment_sha, "application_configuration_mismatch")
            need(row["exit_code"] == 0 and row["capture_status"] == "complete", "application_incomplete")
            start, end = _interval(row, maximum_ns=5_000_000_000)
            need(_utc(context["started_utc"]) <= start <= end <= _utc(context["completed_utc"])
                 and context["started_monotonic_ns"] <= row["started_monotonic_ns"]
                 <= row["completed_monotonic_ns"] <= context["completed_monotonic_ns"], "application_outside_capture")
            input_record = row["input"]
            need(input_record["member"] in members, "input_member_missing")
            bound(members[input_record["member"]], input_record, "input_byte_mismatch")
            need(input_record["read_complete"] is True
                 and input_record["read_sha256"] == input_record["sha256"]
                 and input_record["read_size_bytes"] == input_record["size_bytes"], "input_read_mismatch")
            need((row["arguments_sha256"], row["command_sha256"]) == invocation_binding(selection, app, input_record),
                 "invocation_binding_mismatch")
            for role, prefix, extension in (("snapshot", "snapshots", ".json"),
                                             ("metadata", "metadata", ".json"),
                                             ("stderr", "diagnostics", ".stderr")):
                descriptor = row[role]
                name = prefix + "/" + app + extension
                need(descriptor["member"] == name, "output_member_mismatch")
                raw = members[name]
                need(len(raw) <= 4096, "application_output_size_limit")
                bound(raw, descriptor, "output_byte_mismatch")
                if role != "stderr":
                    value = parse(raw)
                    if role == "snapshot":
                        snapshot_domain(value)
                        need(canonical_bytes(value) == raw, "snapshot_not_canonical")
                state_ids.append(descriptor["state_id"])
        need(len(state_ids) == len(set(state_ids)) and not (set(state_ids) & declared_states),
             "state_identity_reused")
        declared_states.update(state_ids)
    return applications


def _source(source):
    return {"source_kind": "repository_file", "identity_status": "exact",
            "source_path_or_uri": source["path"], "source_revision": source["source_revision"],
            "source_sha256": source["sha256"], "action_repository": None, "action_ref": None,
            "action_commit_sha": None, "container_image_digest": None}


def _runtime_packet(selection, selection_sha, carrier_sha, context, applications, cases):
    acquisition = selection["acquisition_id"]
    key = "STANDALONE_OPERATOR=" + acquisition + "|ATTEMPT=1"
    collector_key = "STANDALONE_COLLECTOR=" + acquisition + "|ATTEMPT=1"
    subject = {"subject_profile": PROFILE, "repository": selection["repository"],
               "source_commit": selection["source_commit"], "acquisition_id": acquisition,
               "acquisition_attempt": 1, "subject_run_key": key, "protocol_id": PROTOCOL_ID,
               "selection_sha256": selection_sha, "release_candidate_id": None,
               "run_mode": "standalone_operator", "active_policy_sets": []}
    source_by_role = {item["role"]: item for item in selection["sources"] if item["role"] in {"worker", "collector"}}
    collector = context["collector"]
    env = selection["environment"]
    environment = {"environment_kind": "unknown", "identity_status": "partial",
                   "os_name": env["os_name"], "os_version": None, "architecture": env["architecture"],
                   "runtime_name": env["python_implementation"], "runtime_version": env["python_version"],
                   "image_identity": None, "image_digest": None,
                   "environment_sha256": sha(canonical_bytes(env)), "raw_environment_included": False}
    executions, states = [], []

    def state(descriptor, producer, observed_at):
        return {"state_id": descriptor["state_id"], "state_type": "other",
                "path_or_uri": "sha256:" + carrier_sha + "!/" + descriptor["member"],
                "content_status": "exact_digest", "sha256": descriptor["sha256"],
                "size_bytes": descriptor["size_bytes"], "media_type": "application/json"
                if descriptor["member"].endswith(".json") else "application/octet-stream",
                "schema_identity": None, "producer_execution_id": producer,
                "observer_execution_id": collector["execution_id"], "subject_run_key": key,
                "release_candidate_id": None, "authority_bearing": False,
                "mutation_class": "advisory_output" if producer else "none",
                "observed_at_utc": observed_at, "secret_material_included": False}

    def execution(row, *, observer=False):
        times = context if observer else row
        return {"execution_id": row["execution_id"],
                "execution_scope": "observation_collector" if observer else "subject",
                "execution_kind": "observer_execution" if observer else "local_tool_execution",
                "parent_execution_id": None, "workflow_name": None, "job_name": None,
                "job_id": None, "job_attempt": None, "step_name": None, "step_number": None,
                "source_identity": _source(source_by_role["collector" if observer else "worker"]),
                "command_identity": {"command_kind": "python_script", "display_name": row["source_path"],
                                     "command_sha256": row["command_sha256"],
                                     "arguments_sha256": row["arguments_sha256"], "raw_command_included": False},
                "execution_environment": dict(environment),
                "run_binding": {"execution_run_key": collector_key if observer else key,
                                "subject_run_key": key,
                                "binding_mode": "external_export" if observer else "current_subject_run",
                                "binding_complete": True},
                "timing": {"timing_status": "partial", "started_utc": times["started_utc"],
                           "completed_utc": times["completed_utc"], "duration_ms": None,
                           "timestamp_source": "tool_reported", "duration_source": "unknown"},
                "result": {"result_status": "complete", "lifecycle_status": "completed",
                           "outcome": "success", "exit_code": row["exit_code"]},
                "declared_role": "observer" if observer else "transition",
                "permitted_mutation_authority": "advisory_output",
                "input_state_ids": [] if observer else [row["input"]["state_id"]],
                "output_state_ids": [] if observer else sorted(row[role]["state_id"]
                                                               for role in ("snapshot", "metadata", "stderr")),
                "external_call_ids": [], "model_inference_ids": [], "resource_measurement_ids": [],
                "capture_status": "complete"}

    for cid in sorted(cases):
        first = applications[cid + ".first"]
        states.append(state(first["input"], None, first["started_utc"]))
    for app, row in sorted(applications.items()):
        executions.append(execution(row))
        states.extend(state(row[role], row["execution_id"], row["completed_utc"])
                      for role in ("snapshot", "metadata", "stderr"))
    executions.append(execution(collector, observer=True))
    source = source_by_role["collector"]
    packet = {"schema_version": "pulsemech_compute_runtime_observation_packet_v0",
              "packet_type": "pulsemech_compute_runtime_observation_packet", "packet_profile": PROFILE,
              "record_status": selection["record_status"],
              "producer": {"producer_id": "standalone_operator_capture_v0", "producer_name": source["path"],
                           "producer_version": "0.1.0", "producer_source": source["path"],
                           "producer_source_sha256": source["sha256"], "ci_workflow_or_job_identity": None,
                           "collection_mode": "example" if selection["record_status"] == "example" else "tool_wrapper",
                           "producer_execution_id": collector["execution_id"]},
              "packet_identity": {"packet_id": "runtime-observation:standalone:" + acquisition,
                                  "packet_sequence": 0, "packet_scope": "example" if selection["record_status"] == "example" else "subject_run",
                                  "subject_run_key": key, "packet_created_utc": context["completed_utc"],
                                  "previous_packet_sha256": None, "canonicalization": "json-sort-keys-utf8-newline"},
              "subject": subject,
              "observation_boundary": {"target_analysis_level": "runtime_observed", "subject_run_key": key,
                                       "collector_run_key": collector_key, "collector_execution_id": collector["execution_id"],
                                       "collector_mode": "example" if selection["record_status"] == "example" else "tool_wrapper",
                                       "observer_in_subject_totals": False,
                                       "capture_started_utc": context["started_utc"], "capture_completed_utc": context["completed_utc"],
                                       "subject_artifacts_mutated": False},
              "authority_inputs": {},
              "timing_basis": {"timestamps_utc": True, "primary_clock_source": "monotonic_tool_clock",
                               "timestamp_resolution_ms": 1, "cross_source_clock_status": "single_source",
                               "duration_derivation": "tool_reported", "duration_values_estimated": False},
              "privacy_boundary": {"raw_environment_included": False, "secret_values_included": False,
                                   "authorization_headers_included": False, "cookies_included": False,
                                   "request_bodies_included": False, "response_bodies_included": False,
                                   "raw_prompt_text_included": False, "raw_model_output_included": False,
                                   "redaction_applied": False, "redaction_rules_sha256": None},
              "executions": sorted(executions, key=lambda item: item["execution_id"]),
              "state_observations": sorted(states, key=lambda item: item["state_id"]),
              "external_calls": [], "model_inferences": [], "resource_measurements": [],
              "coverage": {"coverage_status": "partial", "expected_job_count": None, "observed_job_count": 0,
                           "expected_step_count": None, "observed_step_count": 0,
                           "execution_records": len(executions), "state_records": len(states),
                           "external_call_records": 0, "model_inference_records": 0, "resource_measurement_records": 0,
                           "missing_execution_ids": [], "unobserved_reasons": ["other", "resource_axis_unavailable"],
                           "resource_axes_observed": [], "resource_axes_unavailable": sorted(standalone.RESOURCE_AXES),
                           "external_call_capture_status": "none", "model_inference_capture_status": "none",
                           "state_digest_capture_status": "complete"}, "errors": [], "ok": True}
    return subject, packet


def _relations(selection, subject, runtime_packet, index, applications, cases):
    execution_map = {row["execution_id"]: row for row in runtime_packet["executions"]}
    case_results, evaluations = [], []
    for cid in sorted(cases):
        first, second = applications[cid + ".first"], applications[cid + ".second"]
        state_id = first["snapshot"]["state_id"]
        consumption = core.assess_runtime_output_consumption(
            index, producer_execution_id=first["execution_id"], required_output_state_ids=[state_id],
            required_consumer_execution_ids={state_id: [second["execution_id"]]})
        need(consumption["status"] == "observed", "derived_consumption_unresolved")
        case_results.append({"case_id": cid, "first_application_id": first["application_id"],
                             "second_application_id": second["application_id"],
                             "first_execution_id": first["execution_id"], "second_execution_id": second["execution_id"],
                             "initial_state_id": first["input"]["state_id"], "intermediate_state_id": state_id,
                             "final_state_id": second["snapshot"]["state_id"],
                             "consumption": consumption, "metric_pass": None})
        for phase, row in (("first", first), ("second", second)):
            actual = execution_map[row["execution_id"]]
            # The command selector is fixed by the selected application ID and
            # declared input role. Its input bytes are verified separately above.
            args_sha, command_sha = invocation_binding(selection, cid + "." + phase, row["input"])
            expectation = {"expectation_kind": "compute_relation",
                           "expectation_scope": {"scope_kind": "subject_run", "subject_run_key": subject["subject_run_key"],
                                                 "subject_source_commit": subject["source_commit"], "release_candidate_id": None},
                           "expected_compute": {"selector": {"command_sha256": command_sha},
                                                "downstream_consumption_required": phase == "first"},
                           "expected_source_identity": _source(next(item for item in selection["sources"] if item["role"] == "worker")),
                           "expected_declared_role": "transition", "expected_mutation_authority": "advisory_output"}
            observation = {"execution_identity": {"command_sha256": actual["command_identity"]["command_sha256"]},
                           "source_identity": actual["source_identity"], "subject_run_key": subject["subject_run_key"],
                           "subject_source_commit": subject["source_commit"], "release_candidate_id": None,
                           "declared_role": actual["declared_role"], "mutation_authority": actual["permitted_mutation_authority"],
                           "coverage_status": "complete", "downstream_consumption": consumption if phase == "first" else {"status": "not_applicable"}}
            evaluation = relation.full_relation_evaluation(
                expectation, [observation], comparison_subject=(subject["repository"], subject["subject_run_key"], subject["source_commit"], None),
                coverage={"execution_coverage_status": "complete"})
            need(evaluation["decisive"] is True and all(value in {"match", "complete", "observed", "not_required", True}
                                                     for value in evaluation.values()), "planned_observed_relation_unresolved")
            evaluations.append({"application_id": row["application_id"], "execution_id": row["execution_id"],
                                "expected_command_sha256": command_sha, "evaluation": evaluation})
    return case_results, evaluations


def rejection_report(code: str) -> dict[str, Any]:
    return {"record_type": "required_gate_idempotence_observation_verification_v0", "status": "rejected",
            "ok": False, "binding_complete": False, "packet_semantics_verified": False,
            "errors": [code], **BOUNDARY}


def verify_observation(*, selection_bytes: bytes, expected_selection_sha256: str,
                       carrier_bytes: bytes, expected_carrier_sha256: str,
                       repository_root: Path | None = None) -> dict[str, Any]:
    need(isinstance(expected_selection_sha256, str) and HEX.fullmatch(expected_selection_sha256) is not None,
         "selection_anchor_invalid")
    need(isinstance(expected_carrier_sha256, str) and HEX.fullmatch(expected_carrier_sha256) is not None,
         "carrier_anchor_invalid")
    need(type(selection_bytes) is bytes and sha(selection_bytes) == expected_selection_sha256,
         "selection_digest_mismatch")
    need(type(carrier_bytes) is bytes and sha(carrier_bytes) == expected_carrier_sha256, "carrier_digest_mismatch")
    selection = parse(selection_bytes)
    members = read_archive(carrier_bytes)
    need(members.get("selection/pre_acquisition_selection.json") == selection_bytes, "embedded_selection_mismatch")
    selected_sources, cases = _selection(selection, members, repository_root=repository_root)
    verify_inventory(members, _expected_members(selection, cases))
    context = parse(members["capture/context.json"])
    receipts = parse(members["capture/application_receipts.json"])
    _contexts(selection, context, receipts, expected_selection_sha256)
    applications = _applications(selection, context, receipts, cases, members)
    subject, runtime_packet = _runtime_packet(selection, expected_selection_sha256, expected_carrier_sha256,
                                             context, applications, cases)
    runtime_bytes = canonical_bytes(runtime_packet)
    try:
        index = standalone.validate_and_index(runtime_bytes, expected_subject=subject, selected_sources=selected_sources)
        case_results, evaluations = _relations(selection, subject, runtime_packet, index, applications, cases)
    except (core.RuntimeIndexError, standalone.StandaloneError) as exc:
        raise VerificationError("standalone_runtime_rejected") from exc
    subject_packet = {"schema_version": "pulsemech_compute_standalone_subject_input_v0",
                      "packet_profile": PROFILE, "record_status": selection["record_status"], "subject": subject,
                      "carrier": {"profile": "standalone_operator_acquisition_v0", "sha256": expected_carrier_sha256,
                                  "size_bytes": len(carrier_bytes), "member_count": len(members)},
                      "selection": {"sha256": expected_selection_sha256, "size_bytes": len(selection_bytes)},
                      "runtime_packet": {"sha256": sha(runtime_bytes), "size_bytes": len(runtime_bytes)},
                      "authority_inputs": {}, **BOUNDARY}
    return {"record_type": "required_gate_idempotence_observation_verification_v0", "status": "accepted",
            "ok": True, "record_status": selection["record_status"], "binding_complete": True,
            "packet_semantics_verified": True, "verification_scope": "selected_bytes_and_recorded_consumption",
            "case_count": 12, "application_count": 24, "observer_count": 1,
            "selection_sha256": expected_selection_sha256, "carrier_sha256": expected_carrier_sha256,
            "source_git_binding_verified": selection["record_status"] == "observed",
            "subject_packet": subject_packet, "runtime_packet": runtime_packet,
            "case_results": case_results,
            "planned_observed_relation": {"profile": "standalone_operator_application_relation_v0",
                                          "relations": evaluations, "relation_count": 24,
                                          "case_path_coverage": "complete", "host_runtime_coverage": "partial"},
            "errors": [], **BOUNDARY}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--selection-sha256", required=True)
    parser.add_argument("--carrier", required=True)
    parser.add_argument("--carrier-sha256", required=True)
    parser.add_argument("--repository-root")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    destination = None
    try:
        safe._supported_platform()
        if args.output:
            destination = safe._output_preflight(args.output)
        report = verify_observation(selection_bytes=safe._read_regular(safe._absolute(args.selection)),
                                    expected_selection_sha256=args.selection_sha256,
                                    carrier_bytes=safe._read_regular(safe._absolute(args.carrier)),
                                    expected_carrier_sha256=args.carrier_sha256,
                                    repository_root=safe._absolute(args.repository_root) if args.repository_root else None)
        status = 0
    except (VerificationError, safe.ContractError) as exc:
        report, status = rejection_report(exc.code), 1
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        report, status = rejection_report("input_invalid"), 1
    try:
        raw = canonical_bytes(report)
        if destination is not None:
            try:
                safe._write_output(*destination, raw)
            except safe.ContractError as exc:
                raw, status = canonical_bytes(rejection_report(exc.code)), 1
        sys.stdout.buffer.write(raw)
        return status
    finally:
        if destination is not None:
            os.close(destination[0])


if __name__ == "__main__":
    raise SystemExit(main())
