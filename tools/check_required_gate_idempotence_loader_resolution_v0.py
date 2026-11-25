#!/usr/bin/env python3
"""Independently replay one bounded original-loader capture; never execute it."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jsonschema
import required_gate_idempotence_loader_resolution_v0 as admission
import required_gate_idempotence_loader_resolution_readout_v0 as readout
import check_required_gate_idempotence_entry_task_guard_v0 as guard
import check_required_gate_idempotence_loader_two_slot_qualification_v0 as hardware
import required_gate_idempotence_exec_stop_hosted_io_v0 as transport

ROOT = Path(__file__).resolve().parents[1]
SELF_REL = "tools/check_required_gate_idempotence_loader_resolution_v0.py"
SCHEMA_REL = "schemas/required_gate_idempotence_loader_resolution_v0.schema.json"
PROFILE, LIMITS = admission.PROFILE, admission.LIMITS
BOUNDARY = copy.deepcopy(admission.BOUNDARY)
CAPTURE_TYPE = "required_gate_idempotence_loader_resolution_capture_v0"
NATIVE_ORIGIN = "native_original_loader_capture"
SCRIPTED_ORIGIN = "scripted_test_backend"
DR6_RESERVED = readout.DR6_RESERVED
PTRACE_OPTIONS = hardware.PTRACE_OPTIONS
GLOBAL_FILES = frozenset((
    "request.json", "attempt_start.json", "source_build.admission.json", "original.admission.json",
    "guard.qualification.json", "two_slot.qualification.json", "guard.program.bin", "guard.install.json",
    "context.before.json", "context.after.json", "observer.exe.bin", "kernel.boot_id.bin",
    "observer.stat.bin", "observer.status.bin", "child.stat.setup.bin", "child.status.setup.bin",
    "child.pidfd.info.bin", "child.fds.setup.json", "backings.prelaunch.json",
    "preload.before.json", "preload.setup.json",
    "setup.debug.before.bin", "exec.event_message.bin", "stdout.bin", "stderr.bin",
))
DIAGNOSTIC_FILES = frozenset(("unexpected.regs.bin", "unexpected.debug.bin", "unexpected.siginfo.bin",
                             "unexpected.event_message.bin"))
RESUME_FILES = frozenset("resume.%02d.debug.bin" % i for i in range(11))


class CaptureError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(value, code):
    if not value:
        raise CaptureError(code)


def canonical(value):
    return admission.canonical(value)


def binding(raw):
    return admission.binding(raw)


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _integer(value, code, minimum=0, maximum=(1 << 63) - 1):
    _need(type(value) is int and minimum <= value <= maximum, code)
    return value


def _digest(value, code):
    _need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, code)


def parse(raw):
    try:
        return admission.parse(raw)
    except ValueError as exc:
        raise CaptureError("loader_resolution_capture_json") from exc


def _checkpoints(capture):
    return ([capture["cp0"]] if capture["cp0"] is not None else []) + capture["returns"] + (
        [capture["entry"]] if capture["entry"] is not None else [])


def raw_limit(name):
    readout.safe_path(name)
    if name == "observer.exe.bin":
        return 64 * 1024 * 1024
    if re.fullmatch(r"native\.[0-9a-f]{64}\.elf", name):
        return max(item["size_bytes"] for item in readout.NATIVE.values())
    if name in ("stdout.bin", "stderr.bin"):
        return 4096
    if name.endswith(".json"):
        return LIMITS["max_control_bytes"]
    if name == "guard.program.bin":
        return 4096
    if name == "kernel.boot_id.bin":
        return 128
    if name.endswith("event_message.bin"):
        return 8
    if ".native.rx.sample" in name:
        return sum(item["size_bytes"] for item in readout.NATIVE.values())
    if ".loader.rx.sample" in name:
        return 160721
    if ".memory.sample" in name:
        return 131072
    if ".regs." in name or name == "unexpected.regs.bin":
        return 216
    if ".debug." in name or name == "unexpected.debug.bin":
        return 48
    if name.endswith("siginfo.bin"):
        return 128
    if ".auxv." in name:
        return 1024
    if ".stack.words." in name:
        return 1072
    if ".stack.strings." in name:
        return len(readout.startup.STRING_BYTES)
    if name.endswith("child.exe.link.bin"):
        return 4096
    return 65536


def _files(capture, capture_bytes, files, request_bytes):
    _need(type(files) is dict and len(files) + 1 <= LIMITS["max_raw_files"],
          "loader_resolution_capture_file_count")
    _need("request.json" in files and "capture.json" not in files,
          "loader_resolution_capture_required_request")
    total = len(capture_bytes)
    # All extents precede the first new raw-body hash.
    for name, raw in files.items():
        maximum = raw_limit(name)
        _need(type(raw) is bytes and len(raw) <= maximum, "loader_resolution_capture_raw_extent")
        total += len(raw)
        _need(total <= LIMITS["max_raw_bytes"], "loader_resolution_capture_total_bytes")
    _same(capture["files"], {name: binding(raw) for name, raw in sorted(files.items())},
          "loader_resolution_capture_manifest")
    _need(files["request.json"] == request_bytes, "loader_resolution_preserved_request")
    references = set()
    for point in _checkpoints(capture):
        readout.checkpoint_files(point, files, complete=False)
        references.update(row["path"] for row in point["raw_files"].values())
        references.update(row["content"]["path"] for row in point["backings"])
        if point["executable"] is not None:
            references.add(point["executable"]["content"]["path"])
    if "backings.prelaunch.json" in files:
        prelaunch = parse(files["backings.prelaunch.json"])
        _need(type(prelaunch) is list and len(prelaunch) <= 6, "loader_resolution_prelaunch_roster")
        for row in prelaunch:
            _need(type(row) is dict and set(row) == readout.BACKING_FIELDS,
                  "loader_resolution_prelaunch_fields")
            references.add(row["content"]["path"])
            readout.referenced_bytes(row["content"], files, max(x["size_bytes"] for x in readout.NATIVE.values()))
    partial = set()
    if capture["status"] == "incomplete":
        # A failing read may preserve its bounded prefix before the producer can
        # attach the completed descriptor to the checkpoint. Keep only roles
        # belonging to an actually started checkpoint; these bytes establish no
        # successful observation or admission.
        for point in _checkpoints(capture):
            phase = point["phase"]
            roles = readout.CP0_ROLES if phase == "cp0" else (
                readout.ENTRY_ROLES if phase == "entry" else readout.RETURN_ROLES)
            partial.update(phase + "." + role for role in roles)
    allowed = references | partial | GLOBAL_FILES | RESUME_FILES | DIAGNOSTIC_FILES
    _need(set(files) <= allowed and references <= set(files), "loader_resolution_capture_raw_roster")
    if capture["status"] == "completed":
        _need(set(files) == references | GLOBAL_FILES | RESUME_FILES,
              "loader_resolution_complete_raw_roster")
    return total


def _schema(capture):
    schema_raw = transport.read_regular(ROOT / SCHEMA_REL, LIMITS["max_control_bytes"])
    schema = parse(schema_raw)
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(capture)
    except (jsonschema.SchemaError, jsonschema.ValidationError) as exc:
        raise CaptureError("loader_resolution_capture_schema") from exc
    return schema_raw


def _journal(capture):
    timing, process = capture["timing"], capture["process"]
    started, finished = timing["started_ns"], timing["finished_ns"]
    _need(started <= finished, "loader_resolution_capture_time_order")
    cleanup = timing["cleanup_started_ns"]
    if cleanup is not None:
        _need(started <= cleanup <= finished, "loader_resolution_cleanup_time_order")
    operations = capture["operations"]
    _need(len(operations) <= LIMITS["max_operations"], "loader_resolution_operation_budget")
    _need(sum(row["op"] == "wait" for row in operations) <= LIMITS["max_wait_records"],
          "loader_resolution_wait_budget")
    previous, resumes, failed, terminal = started, [], False, False
    owned = {row["pid"]: row["pidfd"] for row in process["unexpected_children"]}
    if process["child_pid"] is not None:
        _need(process["child_pid"] not in owned, "loader_resolution_owned_child_alias")
        owned[process["child_pid"]] = process["pidfd"]
    for row in operations:
        now = row["at_ns"]
        _need(previous <= now <= finished, "loader_resolution_operation_time_order")
        previous = now
        op = row["op"]
        cleanup_op = op == "kill" or op == "wait" and row["phase"] == "reap"
        if cleanup_op:
            _need(cleanup is not None and now >= cleanup and row["pid"] in owned,
                  "loader_resolution_cleanup_ownership")
            if op == "kill":
                _need(row["signal"] == 9 and (row["method"] == "owned_pid_fallback" and row["pidfd"] is None
                      or row["method"] == "pidfd_send_signal" and row["pidfd"] == owned[row["pid"]]
                      and row["pidfd"] is not None), "loader_resolution_cleanup_signal")
            continue
        _need(cleanup is None or now < cleanup, "loader_resolution_operation_after_cleanup")
        _need(not failed, "loader_resolution_resume_after_failed_operation")
        if op == "wait":
            wanted = 0x137F if row["phase"] == "setup" else 0x4057F if row["phase"] == "exec" else 0x57F
            if row["pid"] != process["child_pid"] or row["status"] != wanted:
                failed = True
            terminal |= row["phase"] == "event.10"
        elif op == "options":
            _need(row["value"] == PTRACE_OPTIONS, "loader_resolution_ptrace_options")
        elif op == "debug_write":
            register, value = row["register"], row["value"]
            if register in (0, 1):
                _need(row["phase"] == "arming" and 0 < value < 1 << 47,
                      "loader_resolution_debug_target_write")
            elif register == 6:
                _need(value == DR6_RESERVED, "loader_resolution_debug_clear_write")
            else:
                _need(register == 7 and row["phase"] == "arming" and value == 5,
                      "loader_resolution_debug_enable_write")
        elif op == "continue":
            _need(not terminal and row["address"] == row["signal"] == 0,
                  "loader_resolution_forbidden_resume")
            resumes.append(row["after"])
            wanted = ["setup", "cp0", *("return.%02d" % i for i in range(1, 10))]
            _need(resumes == wanted[:len(resumes)] and len(resumes) <= 11,
                  "loader_resolution_continuation_order")
            if capture["entry"] is not None:
                _need(now < capture["entry"]["sample_started_ns"], "loader_resolution_post_entry_resume")
        if op in ("options", "debug_write", "continue") and (row["returncode"] != 0 or row["errno"] != 0):
            failed = True
    return len(resumes)


def _complete_journal(capture, files, decoded):
    process, timing = capture["process"], capture["timing"]
    _need(process["child_pid"] is not None and process["starttime"] is not None
          and process["pidfd"] is not None and process["proc_dir_pinned"] is True
          and process["unexpected_children"] == [], "loader_resolution_complete_owned_process")
    start, cleanup, finish = (timing[key] for key in ("started_ns", "cleanup_started_ns", "finished_ns"))
    _need(cleanup is not None and start < cleanup < finish
          and cleanup - start <= LIMITS["observation_ns"]
          and finish - cleanup <= LIMITS["cleanup_ns"], "loader_resolution_complete_deadline")
    initial = (0, 0, 0, 0, DR6_RESERVED, 0)
    armed = (decoded[0]["return_target"], decoded[0]["entry_target"], 0, 0, DR6_RESERVED, 5)
    readout._debug(files["setup.debug.before.bin"], initial)
    _need(files["exec.event_message.bin"] == struct.pack("<Q", process["child_pid"]),
          "loader_resolution_exec_process_identity")
    rows = iter(capture["operations"])
    previous = start

    def take(expected):
        nonlocal previous
        row = next(rows, None)
        _need(row is not None, "loader_resolution_journal_missing_operation")
        _same({key: val for key, val in row.items() if key != "at_ns"}, expected,
              "loader_resolution_journal_sequence")
        _need(previous <= row["at_ns"] <= finish, "loader_resolution_journal_time")
        previous = row["at_ns"]
        return previous

    def wait(phase, status):
        return take({"op": "wait", "phase": phase, "pid": process["child_pid"], "status": status})

    def write(phase, register, value):
        return take({"op": "debug_write", "phase": phase, "register": register, "value": value,
                     "returncode": 0, "errno": 0})

    def resume(number, after):
        write("resume.%02d" % number, 6, DR6_RESERVED)
        readout._debug(files["resume.%02d.debug.bin" % number], initial if number == 0 else armed)
        return take({"op": "continue", "after": after, "address": 0, "signal": 0,
                     "returncode": 0, "errno": 0})

    def samples(point, stopped):
        a = take({"op": "sample", "phase": point["phase"], "side": "a"})
        b = take({"op": "sample", "phase": point["phase"], "side": "b"})
        _need(stopped <= point["sample_started_ns"] <= a < b <= point["sample_finished_ns"] < cleanup,
              "loader_resolution_checkpoint_window")

    wait("setup", 0x137F)
    take({"op": "options", "value": PTRACE_OPTIONS, "returncode": 0, "errno": 0})
    resume(0, "setup")
    stopped = wait("exec", 0x4057F)
    samples(capture["cp0"], stopped)
    for register, value in ((0, armed[0]), (1, armed[1]), (6, DR6_RESERVED), (7, 5)):
        write("arming", register, value)
    _need(previous <= capture["cp0"]["sample_finished_ns"],
          "loader_resolution_cp0_arming_window")
    resumed = resume(1, "cp0")
    _need(capture["cp0"]["sample_finished_ns"] <= resumed, "loader_resolution_cp0_resume_time")
    for number, point in enumerate([*capture["returns"], capture["entry"]], 1):
        stopped = wait("event.%02d" % number, 0x57F)
        samples(point, stopped)
        if number <= 9:
            resumed = resume(number + 1, point["phase"])
            _need(point["sample_finished_ns"] <= resumed, "loader_resolution_return_resume_time")
    killed = take({"op": "kill", "method": "pidfd_send_signal", "pid": process["child_pid"],
                   "pidfd": process["pidfd"], "signal": 9, "returncode": 0, "errno": 0})
    reaped = wait("reap", 9)
    _need(cleanup <= killed < reaped <= finish and next(rows, None) is None,
          "loader_resolution_terminal_cleanup")


def _qualifications(capture, files, request, origin):
    context, process = capture["context"], capture["process"]
    hardware.validate_context(context)
    for name in ("context.before.json", "context.after.json"):
        _same(parse(files[name]), context, "loader_resolution_current_context")
    _same(binding(files["observer.exe.bin"]), context["observer"], "loader_resolution_observer_bytes")
    _same(context["observer"], {key: request["observer"][key] for key in ("size_bytes", "sha256")},
          "loader_resolution_selected_observer")
    _need(files["kernel.boot_id.bin"] == (context["boot_id"] + "\n").encode("ascii"),
          "loader_resolution_boot_id")
    qraw, hraw = files["guard.qualification.json"], files["two_slot.qualification.json"]
    _need(len(qraw) + len(hraw) <= LIMITS["max_qualification_control_bytes"],
          "loader_resolution_qualification_control_budget")
    expected_sources = [{"path": path, **request["sources"][path]} for path in guard.SOURCE_PATHS]
    guard_report = guard.validate_qualification(qraw, expected_sources=expected_sources,
                                               expected_environment=context)
    qualified = guard.strict(qraw, guard.MAX_QUALIFICATION_BYTES)
    report = hardware.verify_record(record_bytes=hraw, expected_record_sha256=binding(hraw)["sha256"],
                                    expected_context=context)
    observed = hardware.parse(hraw)
    wanted_origin = "native_owned_probe" if origin == NATIVE_ORIGIN else "scripted_test_backend"
    _need(report["complete_mechanics_verified"] is True and observed["evidence_origin"] == wanted_origin,
          "loader_resolution_fresh_two_slot_qualification")
    _need(observed["process"]["observer_pid"] == process["observer_pid"]
          and all(row["parent_pid"] == process["observer_pid"] for row in qualified["cases"]),
          "loader_resolution_qualification_observer_pid")
    _need(qualified["timing"]["finished_ns"] <= observed["timing"]["started_ns"]
          <= observed["timing"]["finished_ns"] <= capture["timing"]["started_ns"],
          "loader_resolution_qualification_time_order")
    attempts = {row["attempt_id"] for row in qualified["cases"]} | {observed["attempt_id"]}
    _need(request["attempt_id"] not in attempts, "loader_resolution_qualification_attempt_reuse")
    identities = {(row["child_pid"], row["starttime"]) for row in qualified["cases"]}
    identities.add((observed["process"]["child_pid"], observed["process"]["starttime"]))
    _need((process["child_pid"], process["starttime"]) not in identities,
          "loader_resolution_qualification_child_reuse")
    current_observer = readout.decoding.proc.parse_proc_stat(files["observer.stat.bin"])
    previous_observer = readout.decoding.proc.parse_proc_stat(bytes.fromhex(observed["raw"]["observer.stat.bin"]["hex"]))
    _same({k: current_observer[k] for k in ("pid", "ppid", "starttime")},
          {k: previous_observer[k] for k in ("pid", "ppid", "starttime")},
          "loader_resolution_qualification_observer_continuity")
    _need(all(row["starttime"] >= current_observer["starttime"] for row in qualified["cases"]),
          "loader_resolution_guard_observer_continuity")
    return {"guard": binding(canonical(guard_report)), "two_slot": binding(hardware.canonical(report))}


def _guard(capture, files, request, decoded):
    process, selected = capture["process"], capture["guard"]
    report = guard.validate_installation(files["guard.install.json"], files["guard.program.bin"],
        expected_pid=process["child_pid"], expected_parent_pid=process["observer_pid"],
        expected_starttime=process["starttime"], expected_launcher_fd=selected["launcher_fd"],
        expected_receipt_fd=selected["receipt_fd"], expected_attempt_id=request["attempt_id"],
        expected_request_sha256=capture["request_sha256"],
        setup_status_bytes=files["child.status.setup.bin"],
        setup_fd_records=guard.strict(files["child.fds.setup.json"]),
        checkpoint_status_bytes=tuple(point["raw_files"]["child.status." + side + ".bin"]
            for point in decoded for side in ("before", "after")))
    normalized = guard.validate_descriptors(guard.strict(files["child.fds.setup.json"]),
        (0, 1, 2, selected["launcher_fd"]), selected["launcher_fd"])
    expected_io = {fd: normalized[fd] for fd in (0, 1, 2)}
    launcher = decoded[0]["backing_identities"][readout.LAUNCHER]["stat"]
    _same({key: normalized[selected["launcher_fd"]]["stat"][key] for key in ("dev", "ino", "mode", "size")},
          {key: launcher[key] for key in ("dev", "ino", "mode", "size")},
          "loader_resolution_guard_launcher_identity")
    prelaunch = readout.validate_preload(parse(files["preload.before.json"]))
    readout.validate_preload(parse(files["preload.setup.json"]), expected=prelaunch)
    for point in decoded:
        _same(point["descriptors"], expected_io, "loader_resolution_inherited_descriptors_changed")
        _same(point["namespaces"], capture["context"]["namespaces"],
              "loader_resolution_child_namespace_changed")
        readout.validate_preload(point["preload"], expected=prelaunch)
    return report


def _complete(capture, files, admitted, origin):
    request, native, static = admitted["request"], admitted["native_files"], admitted["static_record"]
    _need(capture["failure"] is None and capture["cp0"] is not None and capture["entry"] is not None,
          "loader_resolution_complete_checkpoints")
    _need(capture["cp0"]["phase"] == "cp0" and capture["entry"]["phase"] == "entry"
          and [row["phase"] for row in capture["returns"]]
          == ["return.%02d" % i for i in range(1, 10)], "loader_resolution_complete_return_roster")
    process = capture["process"]
    _need(process["observer_pid"] != process["child_pid"], "loader_resolution_observer_child_alias")
    _same(parse(files["attempt_start.json"]), {
        "record_type": "required_gate_idempotence_loader_resolution_attempt_start_v0", "profile": PROFILE,
        "attempt_id": request["attempt_id"], "request_sha256": capture["request_sha256"],
        "observer_pid": process["observer_pid"], "started_ns": capture["timing"]["started_ns"]},
        "loader_resolution_attempt_start")
    preserved = admission.validate_preserved_admission(source_build_bytes=files["source_build.admission.json"],
        original_admission_bytes=files["original.admission.json"], admitted=admitted)
    qualification = _qualifications(capture, files, request, origin)
    decoded = [readout.validate_checkpoint(checkpoint=point, files=files, process=process,
                static_record=static, native_files=native) for point in _checkpoints(capture)]
    baseline = readout._backings(parse(files["backings.prelaunch.json"]), files, native)
    layouts = {}
    previous_finished = capture["timing"]["started_ns"]
    for point in decoded:
        _need(previous_finished <= point["sample_started_ns"], "loader_resolution_checkpoint_order")
        previous_finished = point["sample_finished_ns"]
        _same(point["backing_identities"], baseline, "loader_resolution_current_backing_continuity")
        _need(point["auxv_bytes"] == decoded[0]["auxv_bytes"], "loader_resolution_auxv_continuity")
        for path, layout in point["layouts"].items():
            if path in layouts:
                _same(layout, layouts[path], "loader_resolution_load_bias_continuity")
            layouts[path] = layout
    joins = [point["occurrence_join"] for point in decoded[1:-1]]
    observed = [(row["consumer"], row["dynamic_entry_ordinal"], row["name"]) for row in joins]
    wanted = {(row["consumer"]["path"], row["dynamic_entry_ordinal"], row["name"])
              for row in static["occurrence_bindings"]}
    _need(len(observed) == len(set(observed)) == len(wanted) == 9 and set(observed) == wanted,
          "loader_resolution_exact_occurrence_coverage")
    guard_report = _guard(capture, files, request, decoded)
    _complete_journal(capture, files, decoded)
    _need(files["stdout.bin"] == files["stderr.bin"] == b"", "loader_resolution_original_output")
    segment_count = sum(sum(row["type"] == 1 for row in readout.decoding._headers(native[path]))
                        for path in native)
    _need(segment_count == 24, "loader_resolution_final_segment_cardinality")
    return {"occurrence_joins": joins, "invocation": decoded[0]["invocation"], **preserved,
            "qualification_reports": qualification, "task_guard_report": binding(guard.canonical(guard_report)),
            "final_original_objects": 6, "final_pt_load_occurrences": segment_count,
            "original_rx_samples": 16, "return_rx_samples": 18}


def _verify(*, request_bytes, expected_request_sha256, capture_bytes, expected_capture_sha256,
            files, admission_inputs, accepted_policy_sha256, origin):
    _digest(expected_capture_sha256, "loader_resolution_external_capture_digest")
    _need(type(capture_bytes) is bytes and 0 < len(capture_bytes) <= LIMITS["max_control_bytes"],
          "loader_resolution_capture_control_extent")
    _need(hashlib.sha256(capture_bytes).hexdigest() == expected_capture_sha256,
          "loader_resolution_capture_digest_mismatch")
    capture = parse(capture_bytes)
    # Reject fixture/native relabelling paths before any expensive admission.
    _need(type(capture) is dict and capture.get("evidence_origin") == origin,
          "loader_resolution_evidence_origin")
    schema_raw = _schema(capture)
    _need(canonical(capture) == capture_bytes, "loader_resolution_capture_canonical")
    _same(capture["boundary"], BOUNDARY, "loader_resolution_capture_boundary")
    request = admission.validate_request(request_bytes, expected_request_sha256)
    _need(capture["attempt_id"] == request["attempt_id"]
          and capture["request_sha256"] == expected_request_sha256,
          "loader_resolution_capture_request_binding")
    complete = capture["status"] == "completed"
    _need((complete and capture["failure"] is None) or (not complete and capture["failure"] is not None),
          "loader_resolution_capture_completion_claim")
    total = _files(capture, capture_bytes, files, request_bytes)
    continuations = _journal(capture)
    admitted = admission.reconstruct_admission(request_bytes=request_bytes,
        expected_request_sha256=expected_request_sha256, admission_inputs=admission_inputs,
        accepted_policy_sha256=accepted_policy_sha256)
    facts = _complete(capture, files, admitted, origin) if complete else {"occurrence_joins": []}
    _same(admission.source_bindings(), request["sources"], "loader_resolution_replay_sources_changed")
    _need(transport.read_regular(ROOT / SCHEMA_REL, LIMITS["max_control_bytes"]) == schema_raw,
          "loader_resolution_replay_schema_changed")
    native = complete and origin == NATIVE_ORIGIN
    # Bind the old raw diagnostics and independently reconstructed stable facts
    # separately. New verifier PIDs, descriptor numbers and backend versions
    # must not make a second process produce a different normative report.
    source_facts = {key: value for key, value in admitted["source_build_report"].items()
                    if key not in ("backend_observation", "prior_report")}
    original_facts = {key: value for key, value in admitted["original_admission"].items()
                     if key != "signature_evidence"}
    return {"record_type": "required_gate_idempotence_loader_resolution_verification_v0",
        "profile": PROFILE, "attempt_id": request["attempt_id"], "evidence_origin": origin,
        "status": ("accepted_native_loader_resolution_record" if native else
                   "accepted_scripted_loader_resolution_record" if complete else "preserved_incomplete"),
        "request": binding(request_bytes), "capture": binding(capture_bytes),
        "record_binding_verified": True, "complete_mechanics_verified": complete,
        "native_record_reconstructed": native, "scripted_record_reconstructed": complete and not native,
        "original_loader_capture_completed": native,
        "incomplete_record_preserved": not complete, "failure": capture["failure"],
        "ptrace_cont_count": continuations, "accepted_return_events": 9 if complete else 0,
        "post_entry_resumes": 0 if complete else None, "raw_file_count": len(files), "raw_total_bytes": total,
        "source_build_policy_admitted_for_replay": True,
        "source_build_report": binding(files["source_build.admission.json"])
            if "source_build.admission.json" in files else None,
        "original_admission": binding(files["original.admission.json"])
            if "original.admission.json" in files else None,
        "fresh_source_build_facts": binding(admission.canonical(source_facts)),
        "fresh_original_admission_facts": binding(admission.canonical(original_facts)),
        **facts, **copy.deepcopy(BOUNDARY),
        "consumer_resolution_observed": native, "loader_resolution_verified": native,
        "current_backing_read_records_verified": native, "original_invocation_record_verified": native,
        "original_acquisition_ready": False, "future_host_admitted": False}


def _dispatch(arguments, origin):
    try:
        return _verify(**arguments, origin=origin)
    except CaptureError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, OSError, OverflowError, struct.error, RecursionError) as exc:
        raise CaptureError("loader_resolution_capture_rejected") from exc


def verify_capture(*, request_bytes, expected_request_sha256, capture_bytes, expected_capture_sha256,
                   files, admission_inputs=None, accepted_policy_sha256):
    """Native capture verifier. Authored/scripted origins cannot enter this API."""
    return _dispatch(locals(), NATIVE_ORIGIN)


def verify_scripted_capture(*, request_bytes, expected_request_sha256, capture_bytes, expected_capture_sha256,
                            files, admission_inputs=None, accepted_policy_sha256):
    """Test-only raw reconstruction; all native observation claims remain false."""
    return _dispatch(locals(), SCRIPTED_ORIGIN)


def read_capture_directory(directory):
    directory = Path(directory)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(directory, flags)
    try:
        before = os.fstat(fd)
        names = os.listdir(fd)
        _need(len(names) <= LIMITS["max_raw_files"] + ("verification.json" in names)
              and "capture.json" in names and "attempt.incomplete.json" not in names,
              "loader_resolution_directory_roster")
        for name in names:
            readout.safe_path(name)
        raw = transport.read_regular(directory / "capture.json", LIMITS["max_control_bytes"])
        value = parse(raw)
        _need(type(value) is dict and type(value.get("files")) is dict,
              "loader_resolution_directory_manifest")
        _need("verification.json" not in value["files"] and "capture.json" not in value["files"]
              and set(names) - {"verification.json"} == set(value["files"]) | {"capture.json"},
              "loader_resolution_directory_roster")
        total = len(raw)
        for name, row in value["files"].items():
            _need(type(row) is dict and set(row) == {"size_bytes", "sha256"},
                  "loader_resolution_directory_descriptor")
            size = _integer(row["size_bytes"], "loader_resolution_directory_size", maximum=raw_limit(name))
            total += size
            _need(total <= LIMITS["max_raw_bytes"], "loader_resolution_directory_total")
        files = {}
        for name, row in value["files"].items():
            # The total budget above uses these declared extents, so the I/O
            # limit must use the same extents rather than each role's larger
            # maximum. A small declaration cannot authorize a larger read.
            body = transport.read_regular(directory / name, row["size_bytes"])
            _need(len(body) == row["size_bytes"], "loader_resolution_directory_size_mismatch")
            files[name] = body
        after = os.stat(directory, follow_symlinks=False)
        _need(stat.S_ISDIR(after.st_mode) and (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
              and set(os.listdir(fd)) == set(names), "loader_resolution_directory_changed")
        _need(transport.read_regular(directory / "capture.json", LIMITS["max_control_bytes"]) == raw,
              "loader_resolution_capture_file_changed")
        return raw, files
    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--capture-dir", required=True)
    parser.add_argument("--capture-sha256", required=True)
    parser.add_argument("--accepted-policy-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        request = transport.read_regular(Path(args.request), LIMITS["max_control_bytes"])
        capture, files = read_capture_directory(args.capture_dir)
        report = verify_capture(request_bytes=request, expected_request_sha256=args.request_sha256,
            capture_bytes=capture, expected_capture_sha256=args.capture_sha256, files=files,
            accepted_policy_sha256=args.accepted_policy_sha256)
        transport.write_new(Path(args.output), canonical(report))
    except (ValueError, OSError) as exc:
        print(getattr(exc, "code", "loader_resolution_rejected"), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
