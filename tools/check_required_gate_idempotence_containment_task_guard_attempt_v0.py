#!/usr/bin/env python3
"""Reconstruct one selected task-guard request and its preserved attempt.

This checker reads bytes only. It imports neither the attempt adapter, the
selection preparer nor the native qualifier. Recorded invocation counts and an
acknowledgement do not authenticate owner identity or physical execution.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import os
from pathlib import Path
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_containment_task_guard_selection_v0 as selection

raw = selection.raw
ROOT = Path(__file__).resolve().parents[1]
REQUEST_TYPE = "required_gate_idempotence_containment_task_guard_request_v0"
ATTEMPT_TYPE = "required_gate_idempotence_containment_task_guard_attempt_v0"
REPORT_TYPE = "required_gate_idempotence_containment_task_guard_attempt_verification_v0"
PROFILE = "linux_x86_64_containment_task_guard_attempt_v0"
ACKNOWLEDGEMENT = "QUALIFY_CONTAINMENT_TASK_GUARD_ONLY"
ADAPTER_PATH = "tools/run_required_gate_idempotence_containment_task_guard_attempt_v0.py"
CHECKER_PATH = "tools/check_required_gate_idempotence_containment_task_guard_attempt_v0.py"
SCHEMA_PATH = "schemas/required_gate_idempotence_containment_task_guard_attempt_v0.schema.json"
FROZEN_SOURCES = {
    "docs/compute/required_gate_idempotence_containment_entry_plan_v0/plan_v0.json": (21284, "dee57c7b8e4abf86227404ba4c9efc51ced69633e1128295a2d2cef8b78318e0"),
    "docs/compute/required_gate_idempotence_containment_entry_plan_v0/source_bindings_v0.json": (21350, "80190d88ac4e0b654cd8a315b67062aab171a24f81d9fa99108c6d7351930fd0"),
    "docs/compute/required_gate_idempotence_containment_task_guard_selection_v0/build_policy_v0.json": (2478, "68f439c03b4c4656ca19263db4eef0eccb35bf44fd9a154b6ec038efa5de474e"),
    "docs/compute/required_gate_idempotence_containment_task_guard_v0/contract_v0.json": (12962, "20a17df1c1307ef5113044335ee70b8aa96d7d68322f1acc1fe5e9a18ba8bf64"),
    "schemas/required_gate_idempotence_containment_task_guard_qualification_v0.schema.json": (106453, "da7fa9d873cb8fa4e4ac60c71f45e617e4cfc61969d8ce219aaa83bc7225ae39"),
    "schemas/required_gate_idempotence_containment_task_guard_selection_v0.schema.json": (100064, "9751e91ac2bd1899c96f016cfb64eafd002df0d1e1ea057003698f9c03cd1f99"),
    "schemas/required_gate_idempotence_containment_task_guard_v0.schema.json": (116458, "97b753934024c4253a217ab9e906824d016d6144a27f615f7ed678dc5abada44"),
    "tools/build_required_gate_idempotence_containment_task_probe_v0.py": (34164, "40d9a11437d8f16d4992ac3c5aa421bfff4185f72e92bffbc5864a4c8256ce96"),
    "tools/check_required_gate_idempotence_containment_task_guard_qualification_v0.py": (68660, "27217f92c6c4c42bb09e71213ce50b3ddad4c95da5852a16078b75e9f72a5379"),
    "tools/check_required_gate_idempotence_containment_task_guard_selection_v0.py": (29146, "8eea08c92a6fa524e2466c7942274f6b3a2bdc5327b9d4aa9bfa77dddc63d2fc"),
    "tools/check_required_gate_idempotence_containment_task_guard_v0.py": (40713, "5be04d1fbf22c9de4ae0a93d9348ef0740568b68be9c3d60c6027dedb04085ad"),
    "tools/prepare_required_gate_idempotence_containment_task_guard_selection_v0.py": (14178, "54132f4e11ba4bf288db3c3a0e1a7a0e9ba89f86e221dedeca17df0a2f7006f8"),
    "tools/qualify_required_gate_idempotence_containment_task_guard_v0.py": (49570, "0265f67d6bc73cbdd5f57424a8fde1baf3c2ff8707cca55853cc7c734797ff0a"),
    "tools/required_gate_idempotence_containment_startup_v0.c": (27461, "0ae15697c524fc13c2ac0f04d2a1c1d44c7e5952e6b285a4add2799a740d4409"),
    "tools/required_gate_idempotence_containment_task_guard_v0.py": (19568, "b073d370c8081337cb658929a53802bdbfa73d4f0bf4bf677dc716ef9dd76802"),
    "tools/required_gate_idempotence_containment_task_probe_v0.c": (17330, "98e9def65d5679a735f134799fb43f6d6c36b0eb53c240f02b7a1ca273db7f77"),
}
SOURCE_PATHS = tuple(sorted((*FROZEN_SOURCES, ADAPTER_PATH, CHECKER_PATH, SCHEMA_PATH)))
CONTROL_LIMIT = 131072
SOURCE_LIMIT = 1048576
QUALIFICATION_LIMIT = raw.LIMITS["record_bytes"]
INPUT_LIMITS = {"selection": 65536, "build_record": 2097152,
                "probe": 262144, "policy": 65536}
LIMITS = {"attempts": 1, "retries": 0, "request_bytes": CONTROL_LIMIT,
          "attempt_bytes": CONTROL_LIMIT, "qualification_bytes": QUALIFICATION_LIMIT,
          "qualification_limits": dict(raw.LIMITS)}
BOUNDARY = {
    **raw.BOUNDARY,
    "compiler_closure_verified": False,
    "observer_runtime_closure_verified": False,
    "compiler_execution_authenticated": False,
    "build_provenance_authenticated": False,
    "container_image_authenticated": False,
    "outer_security_policy_authenticated": False,
    "owner_identity_authenticated": False,
    "invocation_count_physically_authenticated": False,
}
BUNDLE_FILES = ("request.json", "attempt.json", "selection.json", "build_record.json",
                "probe.elf", "policy.json")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[0-9a-f]{32}\Z")
_CODE = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")
_READ_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW


class AttemptError(ValueError):
    def __init__(self, code):
        self.code = code if code.startswith("containment_guard_attempt_") else "containment_guard_attempt_" + code
        super().__init__(self.code)


def need(condition, code):
    if not condition:
        raise AttemptError(code)


def canonical(value):
    return selection.canonical(value)


def binding(value):
    need(type(value) is bytes, "bytes_required")
    return {"size_bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def parse(value, maximum=CONTROL_LIMIT):
    try:
        return selection.parse(value, maximum)
    except selection.SelectionError as exc:
        raise AttemptError("invalid_control") from exc


def _keys(value, expected, code):
    need(type(value) is dict and set(value) == set(expected), code)


def _same(value, expected, code):
    try:
        need(canonical(value) == canonical(expected), code)
    except AttemptError:
        raise
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise AttemptError(code) from exc


def _integer(value, low, high, code):
    need(type(value) is int and low <= value <= high, code)


def _digest(value, code="digest"):
    need(type(value) is str and _HASH.fullmatch(value) is not None, code)


def _bound(value, expected, maximum, name):
    _digest(expected, name + "_digest")
    need(type(value) is bytes and 0 < len(value) <= maximum, name + "_extent")
    need(binding(value)["sha256"] == expected, name + "_binding")


def _descriptor(value, maximum, code):
    _keys(value, ("size_bytes", "sha256"), code + "_shape")
    _integer(value["size_bytes"], 1, maximum, code + "_size")
    _digest(value["sha256"], code + "_digest")


def _failure(value, *, optional=False):
    need(optional and value is None or type(value) is str and _CODE.fullmatch(value) is not None,
         "failure_code")


def _inventory(value, *, empty=False):
    need(type(value) is list, "source_inventory")
    if empty and not value:
        return
    need(len(value) == len(SOURCE_PATHS), "source_inventory_extent")
    for row, path in zip(value, SOURCE_PATHS):
        _keys(row, ("path", "size_bytes", "sha256"), "source_inventory_row")
        need(row["path"] == path, "source_inventory_order")
        _descriptor({k: row[k] for k in ("size_bytes", "sha256")}, SOURCE_LIMIT, "source")
        if path in FROZEN_SOURCES:
            size, sha = FROZEN_SOURCES[path]
            need(row["size_bytes"] == size and row["sha256"] == sha, "frozen_source_changed")


def source_bytes(root=ROOT):
    selected = {path: selection.read_file(Path(root) / path, SOURCE_LIMIT) for path in SOURCE_PATHS}
    source_inventory(inputs=selected)
    return selected


def source_inventory(inputs=None, root=ROOT):
    selected = source_bytes(root) if inputs is None else dict(inputs)
    _keys(selected, SOURCE_PATHS, "source_roster")
    for path in SOURCE_PATHS:
        need(type(selected[path]) is bytes and 0 < len(selected[path]) <= SOURCE_LIMIT, "source_extent")
    rows = [{"path": path, **binding(selected[path])} for path in SOURCE_PATHS]
    _inventory(rows)
    return rows


def verify_sources(source_inputs=None):
    selected = source_bytes() if source_inputs is None else dict(source_inputs)
    inventory = source_inventory(inputs=selected)
    need(selected == source_bytes(), "source_snapshot_mismatch")
    return inventory


def _input_values(selection_bytes, expected_selection_sha256, build_record_bytes,
                  expected_build_record_sha256, probe_bytes, expected_probe_sha256,
                  policy_bytes, accepted_policy_sha256):
    values = {"selection": selection_bytes, "build_record": build_record_bytes,
              "probe": probe_bytes, "policy": policy_bytes}
    expected = {"selection": expected_selection_sha256,
                "build_record": expected_build_record_sha256,
                "probe": expected_probe_sha256, "policy": accepted_policy_sha256}
    for name in INPUT_LIMITS:
        _digest(expected[name], name + "_expected_digest")
        need(type(values[name]) is bytes and 0 < len(values[name]) <= INPUT_LIMITS[name],
             name + "_extent")
    return values, expected


def _request_value(values, expected, request_id, execution_mode, inventory):
    need(type(request_id) is str and _ID.fullmatch(request_id) is not None, "request_id")
    need(execution_mode in ("native", "scripted") and type(execution_mode) is str, "execution_mode")
    return {"record_type": REQUEST_TYPE, "profile": PROFILE, "request_id": request_id,
            "acknowledgement": ACKNOWLEDGEMENT, "execution_mode": execution_mode,
            "bindings": {name: binding(value) for name, value in values.items()},
            "expected_sha256": dict(expected), "sources": copy.deepcopy(inventory),
            "limits": copy.deepcopy(LIMITS), "boundary": dict(BOUNDARY)}


def _request_shape(value):
    _keys(value, ("record_type", "profile", "request_id", "acknowledgement", "execution_mode",
                  "bindings", "expected_sha256", "sources", "limits", "boundary"), "request_shape")
    need(value["record_type"] == REQUEST_TYPE and value["profile"] == PROFILE, "request_type")
    need(value["acknowledgement"] == ACKNOWLEDGEMENT, "acknowledgement")
    need(type(value["request_id"]) is str and _ID.fullmatch(value["request_id"]) is not None, "request_id")
    need(value["execution_mode"] in ("native", "scripted"), "execution_mode")
    _keys(value["bindings"], INPUT_LIMITS, "request_bindings")
    _keys(value["expected_sha256"], INPUT_LIMITS, "request_expected_digests")
    for name, maximum in INPUT_LIMITS.items():
        _descriptor(value["bindings"][name], maximum, name)
        _digest(value["expected_sha256"][name], name + "_expected_digest")
    _inventory(value["sources"])
    _same(value["limits"], LIMITS, "request_limits")
    _same(value["boundary"], BOUNDARY, "boundary")


def derive_request(*, selection_bytes, expected_selection_sha256, build_record_bytes,
                   expected_build_record_sha256, probe_bytes, expected_probe_sha256,
                   policy_bytes, accepted_policy_sha256, request_id, execution_mode,
                   source_inputs=None):
    """Bind actual inputs and caller expectations without admitting their match."""
    values, expected = _input_values(selection_bytes, expected_selection_sha256,
        build_record_bytes, expected_build_record_sha256, probe_bytes,
        expected_probe_sha256, policy_bytes, accepted_policy_sha256)
    result = _request_value(values, expected, request_id, execution_mode, verify_sources(source_inputs))
    _request_shape(result)
    need(len(canonical(result)) <= CONTROL_LIMIT, "request_extent")
    return result


def verify_request(*, request_bytes, expected_request_sha256, selection_bytes,
                   expected_selection_sha256, build_record_bytes,
                   expected_build_record_sha256, probe_bytes, expected_probe_sha256,
                   policy_bytes, accepted_policy_sha256, source_inputs=None):
    """Freshly reconstruct input admission; do not sample the live context."""
    _bound(request_bytes, expected_request_sha256, CONTROL_LIMIT, "request")
    request = parse(request_bytes)
    _request_shape(request)
    values, expected = _input_values(selection_bytes, expected_selection_sha256,
        build_record_bytes, expected_build_record_sha256, probe_bytes,
        expected_probe_sha256, policy_bytes, accepted_policy_sha256)
    _same(request["expected_sha256"], expected, "external_expectations_changed")
    for name, value in values.items():
        _same(request["bindings"][name], binding(value), name + "_request_binding")
        need(binding(value)["sha256"] == expected[name], name + "_expected_binding")
    inventory = verify_sources(source_inputs)
    _same(request["sources"], inventory, "request_sources")
    selected_sources = source_bytes() if source_inputs is None else dict(source_inputs)
    try:
        report = selection.verify_selection(selection_bytes=selection_bytes,
            expected_selection_sha256=expected_selection_sha256,
            build_record_bytes=build_record_bytes,
            expected_build_record_sha256=expected_build_record_sha256,
            probe_bytes=probe_bytes, expected_probe_sha256=expected_probe_sha256,
            policy_bytes=policy_bytes, accepted_policy_sha256=accepted_policy_sha256,
            source_inputs={path: selected_sources[path] for path in selection.SOURCE_PATHS})
    except (selection.SelectionError, raw.QualificationError) as exc:
        raise AttemptError("selection_rejected") from exc
    need(report["selection_verified"] is True, "selection_not_verified")
    if request["execution_mode"] == "native":
        need(report["evidence_origin"] == "recorded_build_and_local_context", "native_selection_origin")
    need(selected_sources == source_bytes(), "sources_changed_during_admission")
    return request


def _attempt_shape(value):
    _keys(value, ("record_type", "profile", "request", "status", "execution_mode",
                  "invocation_count", "preflight_verified", "environment_before", "environment_after",
                  "sources_before", "sources_after", "qualification", "qualification_verification",
                  "observer_exit_required", "failure", "cleanup_failures", "boundary"), "attempt_shape")
    need(value["record_type"] == ATTEMPT_TYPE and value["profile"] == PROFILE, "attempt_type")
    _descriptor(value["request"], CONTROL_LIMIT, "attempt_request")
    need(value["status"] in ("completed", "incomplete"), "attempt_status")
    need(value["execution_mode"] in ("native", "scripted"), "execution_mode")
    _integer(value["invocation_count"], 0, 1, "invocation_count")
    for name in ("preflight_verified", "observer_exit_required"):
        need(type(value[name]) is bool, name)
    for name in ("environment_before", "environment_after"):
        if value[name] is not None:
            try:
                raw.validate_environment(value[name])
            except raw.QualificationError as exc:
                raise AttemptError(name) from exc
    _inventory(value["sources_before"], empty=True)
    _inventory(value["sources_after"], empty=True)
    if value["qualification"] is not None:
        _descriptor(value["qualification"], QUALIFICATION_LIMIT, "qualification")
    need(value["qualification_verification"] in
         ("not_available", "not_checked", "rejected", "incomplete", "completed"), "qualification_verification")
    _failure(value["failure"], optional=True)
    need(type(value["cleanup_failures"]) is list and len(value["cleanup_failures"]) <= 64, "cleanup_failures")
    for failure in value["cleanup_failures"]:
        _failure(failure)
    _same(value["boundary"], BOUNDARY, "boundary")
    complete = value["status"] == "completed"
    need(value["failure"] is None and not value["cleanup_failures"] if complete
         else value["failure"] is not None, "failure_status")
    if value["invocation_count"] == 0:
        need(not complete and value["qualification"] is None
             and value["qualification_verification"] == "not_available"
             and not value["observer_exit_required"], "zero_invocation_relationship")
    else:
        need(value["preflight_verified"], "invocation_without_preflight")
    if complete:
        need(value["invocation_count"] == 1 and value["preflight_verified"]
             and value["qualification"] is not None
             and value["qualification_verification"] == "completed"
             and not value["observer_exit_required"], "complete_attempt_relationship")
    if value["observer_exit_required"]:
        need(not complete and value["invocation_count"] == 1, "observer_exit_relationship")
    if value["qualification_verification"] == "not_checked":
        need(value["observer_exit_required"] and value["qualification"] is not None,
             "unchecked_qualification_relationship")


def verify_attempt(*, attempt_bytes, expected_attempt_sha256, request_bytes,
                   expected_request_sha256, selection_bytes, expected_selection_sha256,
                   build_record_bytes, expected_build_record_sha256, probe_bytes,
                   expected_probe_sha256, policy_bytes, accepted_policy_sha256,
                   qualification_bytes=None, source_inputs=None):
    """Reconstruct a selected attempt or an explicitly incomplete diagnostic."""
    _bound(attempt_bytes, expected_attempt_sha256, CONTROL_LIMIT, "attempt")
    attempt = parse(attempt_bytes)
    _attempt_shape(attempt)
    _bound(request_bytes, expected_request_sha256, CONTROL_LIMIT, "request")
    request = parse(request_bytes)
    _request_shape(request)
    _same(attempt["request"], binding(request_bytes), "attempt_request_binding")
    need(attempt["execution_mode"] == request["execution_mode"], "attempt_execution_mode")
    if qualification_bytes is None:
        need(attempt["qualification"] is None
             and attempt["qualification_verification"] == "not_available", "qualification_absence")
    else:
        need(type(qualification_bytes) is bytes and 0 < len(qualification_bytes) <= QUALIFICATION_LIMIT,
             "qualification_extent")
        _same(attempt["qualification"], binding(qualification_bytes), "qualification_binding")
        need(attempt["invocation_count"] == 1, "qualification_without_invocation")
    _bound(selection_bytes, expected_selection_sha256, INPUT_LIMITS["selection"], "selection")
    selected = selection.parse(selection_bytes, INPUT_LIMITS["selection"])
    need(type(selected.get("environment")) is dict, "selected_environment")
    if attempt["preflight_verified"]:
        _same(attempt["environment_before"], selected["environment"], "preflight_environment")
        _same(attempt["sources_before"], request["sources"], "preflight_sources")
    complete = attempt["status"] == "completed"
    if complete:
        _same(attempt["environment_after"], selected["environment"], "environment_changed")
        _same(attempt["sources_after"], request["sources"], "sources_changed")
    # Every viable wrapper, including an incomplete one, requires fresh admitted
    # inputs. Cheap malformed/cross-bound controls fail before that reconstruction.
    verified_request = verify_request(request_bytes=request_bytes,
        expected_request_sha256=expected_request_sha256, selection_bytes=selection_bytes,
        expected_selection_sha256=expected_selection_sha256, build_record_bytes=build_record_bytes,
        expected_build_record_sha256=expected_build_record_sha256, probe_bytes=probe_bytes,
        expected_probe_sha256=expected_probe_sha256, policy_bytes=policy_bytes,
        accepted_policy_sha256=accepted_policy_sha256, source_inputs=source_inputs)
    qualification_report = None
    qualification_state = "not_available"
    if qualification_bytes is not None:
        raw_record = None
        try:
            raw_record = raw.parse(qualification_bytes)
        except raw.QualificationError:
            pass
        if type(raw_record) is dict:
            expected_origin = "native_owned_probe" if request["execution_mode"] == "native" else "scripted_test_backend"
            if raw_record.get("evidence_origin") in ("native_owned_probe", "scripted_test_backend"):
                need(raw_record["evidence_origin"] == expected_origin, "qualification_origin")
            exits = raw_record.get("cleanup_failures")
            cases = raw_record.get("cases")
            needs_exit = (type(exits) is list and "task_guard_native_requires_observer_exit" in exits
                          or type(cases) is list and any(type(case) is dict and
                              type(case.get("unresolved_tasks")) is list and case["unresolved_tasks"]
                              for case in cases))
            need(not needs_exit or attempt["observer_exit_required"], "missing_observer_exit")
        try:
            qualification_report = raw.verify_record(record_bytes=qualification_bytes,
                expected_record_sha256=binding(qualification_bytes)["sha256"],
                expected_probe_sha256=expected_probe_sha256,
                expected_environment_sha256=binding(canonical(selected["environment"]))["sha256"])
        except raw.QualificationError:
            qualification_state = "rejected"
        else:
            qualification_state = ("completed" if
                qualification_report["complete_guard_probe_sequence_verified"] else "incomplete")
            # The qualifier may fail before acquiring a context. Every acquired
            # context must identify the selected observer context before success.
            if raw_record["environment"] is not None:
                _same(raw_record["environment"], selected["environment"], "qualification_environment")
            if complete:
                _same(raw_record["environment_after"], selected["environment"], "qualification_environment_after")
    if attempt["qualification_verification"] == "not_checked":
        need(attempt["observer_exit_required"] and qualification_state in ("incomplete", "rejected"),
             "fatal_qualification_state")
    else:
        need(attempt["qualification_verification"] == qualification_state, "qualification_verdict_mismatch")
    if complete:
        need(qualification_state == "completed", "qualification_not_complete")
    need(source_inventory() == verified_request["sources"], "sources_changed_during_replay")
    native = complete and request["execution_mode"] == "native"
    status = ("accepted_native_selected_guard_attempt" if native else
              "accepted_scripted_selected_guard_attempt" if complete else
              "preserved_incomplete_selected_guard_attempt")
    return {"record_type": REPORT_TYPE, "profile": PROFILE, "status": status,
            "request": binding(request_bytes), "attempt": binding(attempt_bytes),
            "selection": binding(selection_bytes), "build_record": binding(build_record_bytes),
            "probe": binding(probe_bytes), "policy": binding(policy_bytes),
            "qualification": binding(qualification_bytes) if qualification_bytes is not None else None,
            "execution_mode": request["execution_mode"], "invocation_count": attempt["invocation_count"],
            "request_verified": True, "selected_attempt_verified": complete,
            "native_selected_guard_attempt_verified": native,
            "qualification_verification": qualification_state,
            "recorded_qualification_verification": attempt["qualification_verification"],
            "qualification_record_verified": qualification_report is not None,
            "complete_guard_probe_sequence_verified": qualification_state == "completed",
            "observer_exit_required": attempt["observer_exit_required"],
            "sources": copy.deepcopy(verified_request["sources"]),
            "qualification_report": qualification_report,
            "evidence_basis": "selected_inputs_and_reconstructed_recorded_invocation_and_raw_transcript",
            **BOUNDARY}


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_uid, info.st_gid, info.st_mtime_ns, info.st_ctime_ns)


def _open_directory(path):
    need(isinstance(path, (str, Path)), "bundle_path")
    path = Path(path)
    need(".." not in path.parts and "\x00" not in str(path)
         and len(str(path)) <= 4096, "bundle_path")
    path = path.absolute()
    descriptor = os.open(path.anchor, _DIR_FLAGS)
    try:
        for component in path.parts[1:]:
            child = os.open(component, _DIR_FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return path, descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_member(directory, name, maximum):
    descriptor = os.open(name, _READ_FLAGS, dir_fd=directory)
    try:
        before = os.fstat(descriptor)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
             and 0 < before.st_size <= maximum, "bundle_member_type_or_extent")
        value = bytearray()
        while len(value) <= maximum:
            block = os.read(descriptor, min(65536, maximum + 1 - len(value)))
            if not block:
                break
            value.extend(block)
        need(len(value) == before.st_size and _identity(before) == _identity(os.fstat(descriptor))
             == _identity(os.stat(name, dir_fd=directory, follow_symlinks=False)), "bundle_member_changed")
        return bytes(value), before
    finally:
        os.close(descriptor)


def verify_bundle(directory, *, expected_attempt_sha256, expected_request_sha256,
                  expected_selection_sha256, expected_build_record_sha256,
                  expected_probe_sha256, accepted_policy_sha256):
    """Read an exact flat bundle through pinned no-follow directory handles."""
    path, descriptor = _open_directory(directory)
    try:
        before = os.fstat(descriptor)
        names = set(os.listdir(descriptor))
        need(names in (set(BUNDLE_FILES), set(BUNDLE_FILES) | {"qualification.json"}), "bundle_inventory")
        limits = {"request.json": CONTROL_LIMIT, "attempt.json": CONTROL_LIMIT,
                  "selection.json": INPUT_LIMITS["selection"],
                  "build_record.json": INPUT_LIMITS["build_record"],
                  "probe.elf": INPUT_LIMITS["probe"], "policy.json": INPUT_LIMITS["policy"],
                  "qualification.json": QUALIFICATION_LIMIT}
        values, identities = {}, {}
        for name in sorted(names):
            values[name], identities[name] = _read_member(descriptor, name, limits[name])
        report = verify_attempt(attempt_bytes=values["attempt.json"],
            expected_attempt_sha256=expected_attempt_sha256, request_bytes=values["request.json"],
            expected_request_sha256=expected_request_sha256, selection_bytes=values["selection.json"],
            expected_selection_sha256=expected_selection_sha256,
            build_record_bytes=values["build_record.json"],
            expected_build_record_sha256=expected_build_record_sha256, probe_bytes=values["probe.elf"],
            expected_probe_sha256=expected_probe_sha256, policy_bytes=values["policy.json"],
            accepted_policy_sha256=accepted_policy_sha256,
            qualification_bytes=values.get("qualification.json"))
        need(set(os.listdir(descriptor)) == names and _identity(os.fstat(descriptor)) == _identity(before),
             "bundle_directory_changed")
        for name in names:
            need(_identity(os.stat(name, dir_fd=descriptor, follow_symlinks=False)) == _identity(identities[name]),
                 "bundle_member_changed")
        _, current = _open_directory(path)
        try:
            need(_identity(os.fstat(current)) == _identity(before), "bundle_path_changed")
        finally:
            os.close(current)
        return report
    finally:
        os.close(descriptor)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--expected-attempt-sha256", required=True)
    parser.add_argument("--expected-request-sha256", required=True)
    parser.add_argument("--expected-selection-sha256", required=True)
    parser.add_argument("--expected-build-record-sha256", required=True)
    parser.add_argument("--expected-probe-sha256", required=True)
    parser.add_argument("--accepted-policy-sha256", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        # A report is a separate derived artifact, never a new bundle member.
        bundle = args.bundle.absolute()
        output = args.out.absolute()
        need(bundle != output and bundle not in output.parents, "report_inside_bundle")
        report = verify_bundle(args.bundle,
            expected_attempt_sha256=args.expected_attempt_sha256,
            expected_request_sha256=args.expected_request_sha256,
            expected_selection_sha256=args.expected_selection_sha256,
            expected_build_record_sha256=args.expected_build_record_sha256,
            expected_probe_sha256=args.expected_probe_sha256,
            accepted_policy_sha256=args.accepted_policy_sha256)
        selection.write_new(args.out, canonical(report))
    except (OSError, AttemptError, selection.SelectionError, raw.QualificationError) as exc:
        print(getattr(exc, "code", "containment_guard_attempt_io"), file=sys.stderr)
        return 2
    return 0 if report["selected_attempt_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
