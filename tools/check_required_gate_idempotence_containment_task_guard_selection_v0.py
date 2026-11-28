#!/usr/bin/env python3
"""Reconstruct a recorded probe build and a selected context without execution.

Repeated byte equality and explicit policy acceptance do not authenticate a
compiler, a build process, source/binary semantics, a host or a native attempt.
This checker never imports the build producer, preparer or native qualifier.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_containment_task_guard_qualification_v0 as raw

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "linux_x86_64_containment_task_guard_selection_v0"
BUILD_TYPE = "required_gate_idempotence_containment_task_probe_build_v0"
SELECTION_TYPE = "required_gate_idempotence_containment_task_guard_selection_v0"
BUILD_REPORT_TYPE = "required_gate_idempotence_containment_task_probe_build_verification_v0"
SELECTION_REPORT_TYPE = "required_gate_idempotence_containment_task_guard_selection_verification_v0"
BUILD_ACK = "BUILD_CONTAINMENT_TASK_PROBE_ONLY"
LATER_ACK = "QUALIFY_CONTAINMENT_TASK_GUARD_ONLY"
PROBE_PATH = raw.PROBE_PATH
BUILD_PATH = "tools/build_required_gate_idempotence_containment_task_probe_v0.py"
PREPARE_PATH = "tools/prepare_required_gate_idempotence_containment_task_guard_selection_v0.py"
CHECKER_PATH = "tools/check_required_gate_idempotence_containment_task_guard_selection_v0.py"
SCHEMA_PATH = "schemas/required_gate_idempotence_containment_task_guard_selection_v0.schema.json"
POLICY_PATH = "docs/compute/required_gate_idempotence_containment_task_guard_selection_v0/build_policy_v0.json"
FROZEN_SOURCES = {
    **raw.FROZEN_SOURCES,
    PROBE_PATH: (17330, "98e9def65d5679a735f134799fb43f6d6c36b0eb53c240f02b7a1ca273db7f77"),
    raw.PRODUCER_PATH: (49570, "0265f67d6bc73cbdd5f57424a8fde1baf3c2ff8707cca55853cc7c734797ff0a"),
    raw.CHECKER_PATH: (68660, "27217f92c6c4c42bb09e71213ce50b3ddad4c95da5852a16078b75e9f72a5379"),
    raw.SCHEMA_PATH: (106453, "da7fa9d873cb8fa4e4ac60c71f45e617e4cfc61969d8ce219aaa83bc7225ae39"),
}
SOURCE_PATHS = tuple(sorted((*FROZEN_SOURCES, BUILD_PATH, PREPARE_PATH, CHECKER_PATH,
                             SCHEMA_PATH, POLICY_PATH)))
CC_FLAGS = (
    "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-ffreestanding",
    "-fno-builtin", "-fno-stack-protector", "-fno-pie", "-no-pie",
    "-fno-asynchronous-unwind-tables", "-fno-unwind-tables", "-nostdlib", "-static",
    "-Wl,--build-id=none", "-Wl,-z,noexecstack", "-Wl,-e,_start",
    "-Wconversion", "-Wshadow",
)
BUILD_ENV = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "TZ": "UTC",
             "SOURCE_DATE_EPOCH": "0", "TMPDIR": "."}
BUILD_LIMITS = {"builds": 2, "retries": 0, "build_seconds": 30, "cleanup_seconds": 5,
                "stdout_bytes": 65536, "stderr_bytes": 65536, "probe_bytes": 262144,
                "compiler_bytes": 67108864, "record_bytes": 2097152}
BOUNDARY = {
    **raw.BOUNDARY,
    "probe_output_executed": False,
    "compiler_closure_verified": False,
    "observer_runtime_closure_verified": False,
    "compiler_execution_authenticated": False,
    "build_provenance_authenticated": False,
    "container_image_authenticated": False,
    "outer_security_policy_authenticated": False,
    "native_qualification_performed": False,
    "native_execution_ready": False,
}
PROBE_SOURCE = {"path": PROBE_PATH, "size_bytes": FROZEN_SOURCES[PROBE_PATH][0],
                "sha256": FROZEN_SOURCES[PROBE_PATH][1]}
POLICY = {
    "record_type": "required_gate_idempotence_containment_task_probe_build_policy_v0",
    "profile": PROFILE,
    "policy_id": "recorded_repeated_probe_build_under_selected_compiler_v0",
    "record_status": "authored_limited_build_acceptance_policy",
    "scope": "fixed_authored_containment_task_guard_probe_only",
    "probe_source": PROBE_SOURCE,
    "recipe": {"flags": list(CC_FLAGS), "source_name": "probe.c", "output_name": "probe.elf",
               "build_ids": ["build-1", "build-2"], "environment": BUILD_ENV,
               "compiler_selection": "external_canonical_path_and_sha256",
               "compiler_execution": "pinned_readonly_regular_file_descriptor",
               "compiler_dependencies": "unverified_declared_builder_trust"},
    "limits": BUILD_LIMITS,
    "acceptance": {"completed_build_record_required": True,
                   "two_distinct_owned_build_directories": True,
                   "actual_probe_bytes_equal": True,
                   "fresh_elf_and_guard_check": True,
                   "source_and_selected_compiler_unchanged": True,
                   "build_origin_preserved": True,
                   "evidence_trust": "recorded_process_and_file_observations_not_physical_authentication"},
    "boundary": BOUNDARY,
}
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_CODE = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")
_IDENTIFIER = re.compile(r"[0-9a-f]{32}\Z")
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
_READ_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK


class SelectionError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(condition, code):
    if not condition:
        raise SelectionError(code if code.startswith("containment_guard_selection_")
                             else "containment_guard_selection_" + code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                       allow_nan=False) + "\n").encode("ascii")


def binding(value):
    need(type(value) is bytes, "bytes_required")
    return {"size_bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def _keys(value, names, code):
    need(type(value) is dict and set(value) == set(names), code)


def _same(value, expected, code):
    need(canonical(value) == canonical(expected), code)


def _integer(value, low, high, code):
    need(type(value) is int and low <= value <= high, code)


def _digest(value, code="digest"):
    need(type(value) is str and _HASH.fullmatch(value) is not None, code)


def _hex(value, maximum, *, empty=False):
    need(type(value) is str and (empty or bool(value)) and len(value) <= 2 * maximum
         and len(value) % 2 == 0 and re.fullmatch(r"[0-9a-f]*", value) is not None,
         "hex_bytes")
    return bytes.fromhex(value)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "duplicate_key")
        result[key] = value
    return result


def _noninteger(_value):
    raise SelectionError("containment_guard_selection_noninteger_json")


def parse(data, maximum=2097152):
    need(type(data) is bytes and 0 < len(data) <= maximum, "json_extent")
    try:
        value = json.loads(data.decode("ascii"), object_pairs_hook=_pairs,
                           parse_float=_noninteger, parse_constant=_noninteger)
    except SelectionError:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise SelectionError("containment_guard_selection_invalid_json") from exc
    need(type(value) is dict, "json_object")
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        need(depth <= 24 and count <= 20000, "json_complexity")
        if type(item) is dict:
            need(all(type(key) is str and 0 < len(key) <= 128 for key in item), "json_key")
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            need(len(item) <= 4096, "json_list")
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            need(len(item) <= 524288, "json_string")
        else:
            need(item is None or type(item) is bool or
                 type(item) is int and -(1 << 64) < item < (1 << 64), "json_scalar")
    need(canonical(value) == data, "noncanonical_json")
    return value


def _bound(data, expected_sha256, maximum, code):
    _digest(expected_sha256, code + "_digest")
    need(type(data) is bytes and 0 < len(data) <= maximum
         and binding(data)["sha256"] == expected_sha256, code + "_binding")


def _path(value):
    need(type(value) is str and 1 < len(value) <= 4096 and value.startswith("/")
         and re.fullmatch(r"/[A-Za-z0-9_.+/-]+", value) is not None
         and all(part not in ("", ".", "..") for part in value.split("/")[1:]),
         "compiler_path")


def _compiler(value):
    _keys(value, ("path", "size_bytes", "sha256"), "compiler_shape")
    _path(value["path"])
    _integer(value["size_bytes"], 64, BUILD_LIMITS["compiler_bytes"], "compiler_extent")
    _digest(value["sha256"], "compiler_digest")


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_uid, info.st_gid, info.st_mtime_ns, info.st_ctime_ns)


def _parent(path):
    path = Path(path)
    need(".." not in path.parts and "\x00" not in str(path), "file_path")
    path = path.absolute()
    need(path.name not in ("", ".", ".."), "file_path")
    descriptors = []
    try:
        parent = os.open(path.anchor, _DIR_FLAGS)
        descriptors.append(parent)
        for part in path.parts[1:-1]:
            parent = os.open(part, _DIR_FLAGS, dir_fd=parent)
            descriptors.append(parent)
        return path, parent, descriptors
    except BaseException:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def read_file(path, maximum):
    _integer(maximum, 1, 67108864, "read_limit")
    path, parent, descriptors = _parent(path)
    try:
        fd = os.open(path.name, _READ_FLAGS, dir_fd=parent)
        descriptors.append(fd)
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
             and 0 < before.st_size <= maximum, "input_file")
        data = bytearray()
        while len(data) <= maximum:
            block = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        need(len(data) == before.st_size and _identity(os.fstat(fd)) == _identity(before),
             "input_changed")
        _, fresh_parent, fresh = _parent(path)
        try:
            current = os.stat(path.name, dir_fd=fresh_parent, follow_symlinks=False)
            need(_identity(current) == _identity(before), "input_path_changed")
        finally:
            for descriptor in reversed(fresh):
                os.close(descriptor)
        return bytes(data)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _invalidate_owned_output(path, selected, fd=None):
    """Invalidate only the new inode, including after an ambiguous close error."""
    if selected is None:
        return
    identity = selected.st_dev, selected.st_ino
    if fd is not None:
        try:
            current = os.fstat(fd)
            if (current.st_dev, current.st_ino) == identity:
                os.ftruncate(fd, 0)
                os.fsync(fd)
                return
        except OSError:
            pass
    opened = []
    try:
        path, parent, opened = _parent(path)
        reopened = os.open(path.name, os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW |
                           os.O_NONBLOCK, dir_fd=parent)
        opened.append(reopened)
        current = os.fstat(reopened)
        if stat.S_ISREG(current.st_mode) and (current.st_dev, current.st_ino) == identity:
            os.ftruncate(reopened, 0)
            os.fsync(reopened)
    except (OSError, SelectionError):
        pass
    finally:
        for descriptor in reversed(opened):
            try:
                os.close(descriptor)
            except OSError:
                pass


def write_new(path, data):
    need(type(data) is bytes and 0 < len(data) <= BUILD_LIMITS["record_bytes"], "output_extent")
    path, parent, descriptors = _parent(path)
    fd = before = None
    try:
        fd = os.open(path.name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC |
                     os.O_NOFOLLOW, 0o600, dir_fd=parent)
        descriptors.append(fd)
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
             and stat.S_IMODE(before.st_mode) == 0o600 and before.st_uid == os.geteuid(),
             "output_identity")
        rest = memoryview(data)
        while rest:
            count = os.write(fd, rest)
            need(count > 0, "output_short_write")
            rest = rest[count:]
        os.fsync(fd)
        need(os.pread(fd, len(data) + 1, 0) == data and read_file(path, len(data)) == data,
             "output_readback")
        current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        public = os.stat(path, follow_symlinks=False)
        need((current.st_dev, current.st_ino, current.st_nlink, current.st_size) ==
             (before.st_dev, before.st_ino, 1, len(data)) and
             (public.st_dev, public.st_ino, public.st_nlink, public.st_size) ==
             (before.st_dev, before.st_ino, 1, len(data)), "output_replaced")
    except BaseException:
        _invalidate_owned_output(path, before, fd)
        raise
    finally:
        active_error = sys.exc_info()[1]
        close_failure = None
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except BaseException as exc:
                close_failure = close_failure or exc
        if close_failure is not None:
            _invalidate_owned_output(path, before, fd)
            if active_error is None:
                raise close_failure


def verify_policy(*, policy_bytes, accepted_policy_sha256):
    _bound(policy_bytes, accepted_policy_sha256, 65536, "accepted_policy")
    value = parse(policy_bytes, 65536)
    _same(value, POLICY, "policy_semantics")
    return value


def source_bytes(root=ROOT):
    selected = {path: read_file(Path(root) / path, 1048576) for path in SOURCE_PATHS}
    source_inventory(inputs=selected)
    return selected


def source_inventory(inputs=None, root=ROOT):
    selected = source_bytes(root) if inputs is None else dict(inputs)
    _keys(selected, SOURCE_PATHS, "source_roster")
    for path in SOURCE_PATHS:
        need(type(selected[path]) is bytes and 0 < len(selected[path]) <= 1048576, "source_extent")
    for path, (size, sha) in FROZEN_SOURCES.items():
        _same(binding(selected[path]), {"size_bytes": size, "sha256": sha}, "frozen_source_changed")
    need(selected[POLICY_PATH] == canonical(POLICY), "policy_source_changed")
    return [{"path": path, **binding(selected[path])} for path in SOURCE_PATHS]


def verify_sources(inputs=None):
    selected = source_bytes() if inputs is None else dict(inputs)
    inventory = source_inventory(inputs=selected)
    need(selected == source_bytes(), "source_snapshot_mismatch")
    try:
        raw.verify_prerequisite_source_contract()
    except raw.QualificationError as exc:
        raise SelectionError("containment_guard_selection_prerequisite_contract") from exc
    need(selected == source_bytes(), "source_changed_during_verification")
    return inventory


def _inventory_shape(value, *, allow_empty=False):
    need(type(value) is list, "inventory_shape")
    if allow_empty and value == []:
        return
    need(len(value) == len(SOURCE_PATHS), "inventory_extent")
    for expected, row in zip(SOURCE_PATHS, value):
        _keys(row, ("path", "size_bytes", "sha256"), "inventory_row")
        need(row["path"] == expected, "inventory_order")
        _integer(row["size_bytes"], 1, 1048576, "inventory_file_size")
        _digest(row["sha256"], "inventory_file_digest")


def _request_value(compiler, policy_bytes, inventory):
    _compiler(compiler)
    return {"profile": PROFILE, "source": copy.deepcopy(PROBE_SOURCE),
            "compiler": copy.deepcopy(compiler),
            "argv": [compiler["path"], *CC_FLAGS, "probe.c", "-o", "probe.elf"],
            "environment": dict(BUILD_ENV), "limits": dict(BUILD_LIMITS),
            "policy": binding(policy_bytes), "sources": copy.deepcopy(inventory)}


def derive_build_request(*, compiler, policy_bytes, accepted_policy_sha256, source_inputs=None):
    verify_policy(policy_bytes=policy_bytes, accepted_policy_sha256=accepted_policy_sha256)
    return _request_value(compiler, policy_bytes, verify_sources(source_inputs))


def _failure(value, *, optional=False):
    need(optional and value is None or type(value) is str and _CODE.fullmatch(value) is not None,
         "failure_code")


def _process(value):
    _keys(value, ("pid", "exit_code", "elapsed_ns", "timed_out", "stdout_overflow",
                  "stderr_overflow", "reaped"), "process_shape")
    _integer(value["pid"], 1, (1 << 31) - 1, "process_pid")
    if value["exit_code"] is not None:
        _integer(value["exit_code"], -255, 255, "process_exit")
    _integer(value["elapsed_ns"], 0, (1 << 64) - 1, "process_elapsed")
    for name in ("timed_out", "stdout_overflow", "stderr_overflow", "reaped"):
        need(type(value[name]) is bool, "process_boolean")
    need(not value["reaped"] or value["exit_code"] is not None, "process_reap_status")
    return (value["exit_code"] == 0 and value["reaped"] is True
            and 0 < value["elapsed_ns"] <= BUILD_LIMITS["build_seconds"] * 1000000000
            and not any(value[name] for name in ("timed_out", "stdout_overflow", "stderr_overflow")))


def _build_row(row, index, request, source):
    _keys(row, ("build_id", "argv", "environment", "source_hex", "source_after_hex",
                "process", "stdout_hex", "stderr_hex", "probe_hex", "directory_verified"), "build_row_shape")
    need(row["build_id"] == "build-" + str(index + 1), "build_order")
    _same(row["argv"], request["argv"], "build_argv")
    _same(row["environment"], BUILD_ENV, "build_environment")
    need(_hex(row["source_hex"], 65536) == source, "build_source")
    after = None if row["source_after_hex"] is None else _hex(row["source_after_hex"], 65536, empty=True)
    _hex(row["stdout_hex"], BUILD_LIMITS["stdout_bytes"], empty=True)
    _hex(row["stderr_hex"], BUILD_LIMITS["stderr_bytes"], empty=True)
    need(type(row["directory_verified"]) is bool, "build_directory_boolean")
    probe = None if row["probe_hex"] is None else _hex(row["probe_hex"], BUILD_LIMITS["probe_bytes"], empty=True)
    complete = _process(row["process"]) and after == source and row["directory_verified"] and bool(probe)
    if complete:
        try:
            raw.verify_probe_elf(probe, expected_probe_sha256=binding(probe)["sha256"])
        except raw.QualificationError:
            complete = False
    return bool(complete), probe


def verify_build_record(*, record_bytes, expected_record_sha256, policy_bytes,
                        accepted_policy_sha256, source_inputs=None):
    verify_policy(policy_bytes=policy_bytes, accepted_policy_sha256=accepted_policy_sha256)
    _bound(record_bytes, expected_record_sha256, BUILD_LIMITS["record_bytes"], "build_record")
    record = parse(record_bytes)
    _keys(record, ("record_type", "profile", "attempt_id", "status", "evidence_origin",
                   "request", "source_hex", "compiler_after", "sources_after", "builds",
                   "failure", "cleanup_failures", "boundary"), "build_record_shape")
    need(record["record_type"] == BUILD_TYPE and record["profile"] == PROFILE, "build_record_type")
    need(type(record["attempt_id"]) is str and _IDENTIFIER.fullmatch(record["attempt_id"]), "build_attempt_id")
    need(record["status"] in ("completed", "incomplete"), "build_status")
    need(record["evidence_origin"] in ("recorded_compile_only", "scripted_build_backend"), "build_origin")
    _same(record["boundary"], BOUNDARY, "build_boundary")
    _failure(record["failure"], optional=True)
    need(type(record["cleanup_failures"]) is list and len(record["cleanup_failures"]) <= 64, "cleanup_failures")
    for failure in record["cleanup_failures"]:
        _failure(failure)
    complete = record["status"] == "completed"
    need(record["failure"] is None and not record["cleanup_failures"] if complete
         else record["failure"] is not None, "build_failure_status")
    inventory = verify_sources(source_inputs)
    _keys(record["request"], ("profile", "source", "compiler", "argv", "environment",
                             "limits", "policy", "sources"), "build_request_shape")
    expected_request = _request_value(record["request"]["compiler"], policy_bytes, inventory)
    _same(record["request"], expected_request, "build_request_selection")
    source = _hex(record["source_hex"], 65536)
    _same(binding(source), {key: PROBE_SOURCE[key] for key in ("size_bytes", "sha256")}, "source_binding")
    _inventory_shape(record["sources_after"], allow_empty=not complete)
    if record["compiler_after"] is not None:
        _compiler(record["compiler_after"])
    if complete:
        _same(record["sources_after"], inventory, "sources_changed")
        _same(record["compiler_after"], expected_request["compiler"], "compiler_changed")
    builds = record["builds"]
    need(type(builds) is list and 0 <= len(builds) <= 2 and (not complete or len(builds) == 2), "build_count")
    outputs = []
    for index, row in enumerate(builds):
        row_complete, probe = _build_row(row, index, expected_request, source)
        need(row_complete or not complete and index == len(builds) - 1, "build_prefix_incomplete")
        outputs.append(probe)
    if complete:
        need(outputs[0] == outputs[1], "repeated_probe_bytes_differ")
    need(source_inventory() == inventory, "sources_changed_during_reconstruction")
    recorded = complete and record["evidence_origin"] == "recorded_compile_only"
    status = ("accepted_recorded_probe_build" if recorded else "accepted_scripted_probe_build") if complete else "preserved_incomplete_probe_build"
    return {"record_type": BUILD_REPORT_TYPE, "profile": PROFILE, "status": status,
            "record": binding(record_bytes), "policy": binding(policy_bytes),
            "probe": binding(outputs[0]) if complete else None, "build_count": len(builds),
            "build_record_verified": complete, "recorded_compile_only": recorded,
            "evidence_origin": record["evidence_origin"], "sources": inventory, **BOUNDARY}


def _selection_value(*, build_record_bytes, expected_build_record_sha256,
                     probe_bytes, expected_probe_sha256, environment, environment_origin,
                     policy_bytes, accepted_policy_sha256, selection_id, source_inputs=None):
    report = verify_build_record(record_bytes=build_record_bytes,
        expected_record_sha256=expected_build_record_sha256, policy_bytes=policy_bytes,
        accepted_policy_sha256=accepted_policy_sha256, source_inputs=source_inputs)
    need(report["build_record_verified"], "incomplete_build_cannot_select")
    _bound(probe_bytes, expected_probe_sha256, BUILD_LIMITS["probe_bytes"], "selected_probe")
    record = parse(build_record_bytes)
    need(probe_bytes == bytes.fromhex(record["builds"][0]["probe_hex"]), "selected_probe_not_build_output")
    try:
        raw.verify_probe_elf(probe_bytes, expected_probe_sha256=expected_probe_sha256)
        raw.validate_environment(environment)
    except raw.QualificationError as exc:
        raise SelectionError("containment_guard_selection_probe_or_environment") from exc
    need(environment_origin in ("local_readonly_context", "scripted_context"), "environment_origin")
    need(type(selection_id) is str and _IDENTIFIER.fullmatch(selection_id), "selection_id")
    origin = ("recorded_build_and_local_context"
              if record["evidence_origin"] == "recorded_compile_only" and environment_origin == "local_readonly_context"
              else "scripted_selection")
    inventory = report["sources"]
    value = {"record_type": SELECTION_TYPE, "profile": PROFILE, "selection_id": selection_id,
             "record_status": "prepared", "evidence_origin": origin,
             "environment_origin": environment_origin, "environment": copy.deepcopy(environment),
             "bindings": {"build_record": binding(build_record_bytes), "probe": binding(probe_bytes),
                          "environment": binding(canonical(environment)), "policy": binding(policy_bytes)},
             "compiler": copy.deepcopy(record["request"]["compiler"]),
             "probe_source": copy.deepcopy(PROBE_SOURCE), "build_evidence_origin": record["evidence_origin"],
             "qualification": {"profile": raw.PROFILE, "acknowledgement": LATER_ACK,
                               "limits": dict(raw.LIMITS), "cases": list(raw.CASES),
                               "sources": [copy.deepcopy(row) for row in inventory if row["path"] in raw.SOURCE_PATHS]},
             "sources": copy.deepcopy(inventory), "boundary": copy.deepcopy(BOUNDARY)}
    need(source_inventory() == inventory, "sources_changed_during_selection")
    need(len(canonical(value)) <= 65536, "selection_extent")
    return value


def derive_selection(**arguments):
    return _selection_value(**arguments)


def verify_selection(*, selection_bytes, expected_selection_sha256, build_record_bytes,
                     expected_build_record_sha256, probe_bytes, expected_probe_sha256,
                     policy_bytes, accepted_policy_sha256, source_inputs=None):
    _bound(selection_bytes, expected_selection_sha256, 65536, "selection")
    value = parse(selection_bytes, 65536)
    _keys(value, ("record_type", "profile", "selection_id", "record_status", "evidence_origin",
                  "environment_origin", "environment", "bindings", "compiler", "probe_source",
                  "build_evidence_origin", "qualification", "sources", "boundary"), "selection_shape")
    expected = _selection_value(build_record_bytes=build_record_bytes,
        expected_build_record_sha256=expected_build_record_sha256, probe_bytes=probe_bytes,
        expected_probe_sha256=expected_probe_sha256, environment=value["environment"],
        environment_origin=value["environment_origin"], policy_bytes=policy_bytes,
        accepted_policy_sha256=accepted_policy_sha256, selection_id=value["selection_id"],
        source_inputs=source_inputs)
    _same(value, expected, "selection_relationship")
    return {"record_type": SELECTION_REPORT_TYPE, "profile": PROFILE,
            "status": "accepted_recorded_guard_selection" if value["evidence_origin"] ==
                      "recorded_build_and_local_context" else "accepted_scripted_guard_selection",
            "selection": binding(selection_bytes), **copy.deepcopy(value["bindings"]),
            "evidence_origin": value["evidence_origin"], "build_record_verified": True,
            "selection_verified": True, "sources": copy.deepcopy(value["sources"]), **BOUNDARY}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_subparsers(dest="mode", required=True)
    for name in ("build", "selection"):
        command = mode.add_parser(name)
        command.add_argument("--build-record", type=Path, required=True)
        command.add_argument("--expected-build-record-sha256", required=True)
        command.add_argument("--policy", type=Path, required=True)
        command.add_argument("--accepted-policy-sha256", required=True)
        command.add_argument("--out", type=Path, required=True)
        if name == "selection":
            command.add_argument("--selection", type=Path, required=True)
            command.add_argument("--expected-selection-sha256", required=True)
            command.add_argument("--probe", type=Path, required=True)
            command.add_argument("--expected-probe-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        record = read_file(args.build_record, BUILD_LIMITS["record_bytes"])
        policy = read_file(args.policy, 65536)
        if args.mode == "build":
            report = verify_build_record(record_bytes=record,
                expected_record_sha256=args.expected_build_record_sha256,
                policy_bytes=policy, accepted_policy_sha256=args.accepted_policy_sha256)
        else:
            report = verify_selection(selection_bytes=read_file(args.selection, 65536),
                expected_selection_sha256=args.expected_selection_sha256,
                build_record_bytes=record, expected_build_record_sha256=args.expected_build_record_sha256,
                probe_bytes=read_file(args.probe, BUILD_LIMITS["probe_bytes"]),
                expected_probe_sha256=args.expected_probe_sha256, policy_bytes=policy,
                accepted_policy_sha256=args.accepted_policy_sha256)
        write_new(args.out, canonical(report))
    except (OSError, SelectionError, raw.QualificationError) as exc:
        print(getattr(exc, "code", "containment_guard_selection_io"), file=sys.stderr)
        return 2
    return 0 if report["build_record_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
