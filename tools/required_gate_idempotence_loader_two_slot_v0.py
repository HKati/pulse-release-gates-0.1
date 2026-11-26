#!/usr/bin/env python3
"""Data-only validation of authored two-slot mechanics fixtures.

This module never runs the inert probe, calls ptrace, reads a live process or
qualifies a host.  Even a complete accepted fixture leaves all live qualification
and original-acquisition boundaries false.  The supplied raw files are the only
evidence read by ``verify_transcript``.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct


RECORD_TYPE = "required_gate_idempotence_loader_two_slot_fixture_transcript_v0"
PROFILE = "linux_x86_64_loader_two_slot_fixture_v0"
DR6_RESERVED = 0xFFFF0FF0
PTRACE_OPTIONS = 0x10001E
PROBE_BASE = 0x400000
PROBE_ENTRY = PROBE_BASE + 0x80
PROBE_CODE = bytes.fromhex("b90900000090e2fd0f0b")
SLOT0_TARGET = PROBE_ENTRY + 5
SLOT1_TARGET = PROBE_ENTRY + 8
CONTROL_BYTES = 1024 * 1024
MAX_INTEGER = (1 << 63) - 1

BOUNDARY = {
    "two_slot_breakpoint_qualified": False,
    "rflags_resume_policy_qualified": False,
    "original_acquisition_ready": False,
    "consumer_resolution_observed": False,
    "source_build_gate_satisfied": False,
    "native_acquisition_performed": False,
    "physical_execution_authenticated": False,
    "metric_pass": None,
    "authority_effect": "none",
}

POLICY = {
    "record_type": RECORD_TYPE,
    "profile": PROFILE,
    "evidence_origin": "authored_test_fixture",
    "probe_entry": PROBE_ENTRY,
    "return_target": SLOT0_TARGET,
    "terminal_target": SLOT1_TARGET,
    "accepted_return_events": 9,
    "maximum_preserved_return_events": 10,
    "completed_total_ptrace_cont": 11,
    "post_entry_resumes": 0,
    "allowed_debug_writes": [0, 1, 6, 7],
    "armed_dr7": 5,
    "dr6_reserved": DR6_RESERVED,
    "ptrace_options": PTRACE_OPTIONS,
    "register_bytes": 216,
    "debug_register_bytes": 48,
    "siginfo_bytes": 128,
    "stable_samples": 2,
    "rflags_trap_flag_mask": 0x100,
    "rflags_trap_flag_must_be_clear": True,
    "rflags_resume_policy_qualified": False,
    "rflags_resume_flag_policy": "not_qualified_no_live_RF_value_selected",
    "observation_nanoseconds": 15_000_000_000,
    "cleanup_nanoseconds": 2_000_000_000,
    "wait_records": 20,
    "raw_files": 160,
    "raw_total_bytes": CONTROL_BYTES,
    "control_bytes": CONTROL_BYTES,
    "fixture_acceptance_is_live_qualification": False,
}


class TwoSlotError(ValueError):
    """Stable rejection reason without raw data or inspected identities."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise TwoSlotError(code)


def _keys(value, expected, code):
    expected = set(expected)
    _need(type(value) is dict and len(value) == len(expected)
          and all(type(key) is str for key in value) and set(value) == expected, code)


def _integer(value, code, minimum=0, maximum=MAX_INTEGER):
    _need(type(value) is int and minimum <= value <= maximum, code)
    return value


def _same(actual, expected, code):
    _need(type(actual) is type(expected) and actual == expected, code)


def _canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def _binding(raw):
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        _need(key not in value, "two_slot_duplicate_key")
        value[key] = item
    return value


def _invalid_number(_value):
    raise TwoSlotError("two_slot_number")


def _json_tree(value):
    pending = [(value, 0)]
    remaining = 20_000
    while pending:
        item, depth = pending.pop()
        remaining -= 1
        _need(remaining >= 0 and depth <= 12, "two_slot_control_structure")
        if type(item) is dict:
            _need(len(item) <= POLICY["raw_files"], "two_slot_control_structure")
            for key, child in item.items():
                _need(type(key) is str and len(key) <= 128, "two_slot_control_key")
                pending.append((child, depth + 1))
        elif type(item) is list:
            _need(len(item) <= POLICY["raw_files"], "two_slot_control_structure")
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            _need(len(item) <= 4096, "two_slot_control_string")
        else:
            _need(item is None or type(item) is bool or
                  (type(item) is int and -MAX_INTEGER <= item <= MAX_INTEGER),
                  "two_slot_control_type")


def probe_bytes():
    """Return a fixed authored ELF; constructing it does not execute it.

    MOV ECX,9; NOP; LOOP NOP; UD2.  The terminal instruction is deliberately
    inert-by-failure and must never be resumed after the slot-1 stop.
    """
    ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    size = 0x80 + len(PROBE_CODE)
    header = ident + struct.pack("<HHIQQQIHHHHHH", 2, 62, 1, PROBE_ENTRY,
                                64, 0, 0, 64, 56, 1, 0, 0, 0)
    segment = struct.pack("<IIQQQQQQ", 1, 5, 0, PROBE_BASE, PROBE_BASE,
                          size, size, 4096)
    return header + segment + bytes(8) + PROBE_CODE


def _probe_layout(raw):
    expected = probe_bytes()
    _need(type(raw) is bytes and len(raw) == len(expected) and raw == expected,
          "two_slot_probe_bytes")
    entry, phoff = struct.unpack_from("<QQ", raw, 24)
    kind, flags, offset, base, physical, filesz, memsz, alignment = struct.unpack_from(
        "<IIQQQQQQ", raw, phoff)
    _need((kind, flags, offset, physical, filesz, memsz, alignment) ==
          (1, 5, 0, base, len(raw), len(raw), 4096), "two_slot_probe_segment")
    code_offset = entry - base
    code = raw[code_offset:]
    count = struct.unpack_from("<I", code, 1)[0]
    displacement = struct.unpack_from("<b", code, 7)[0]
    _need(code[0] == 0xB9 and count == 9 and code[5:7] == b"\x90\xe2"
          and 8 + displacement == 5 and code[8:] == b"\x0f\x0b",
          "two_slot_probe_control_flow")
    return {"entry": entry, "return": entry + 5, "terminal": entry + 8,
            "code": code, "visits": count}


def _descriptor(value):
    _keys(value, ("size_bytes", "sha256"), "two_slot_file_descriptor")
    _integer(value["size_bytes"], "two_slot_file_size", 1, CONTROL_BYTES)
    _need(type(value["sha256"]) is str and
          re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None,
          "two_slot_file_digest")


def _expected_files(event_count, resume_count):
    names = {"probe.elf", "child.pidfd.info.bin", "child.stat.setup.bin",
             "child.status.setup.bin", "cp0.child.stat.bin", "cp0.child.status.bin",
             "cp0.regs.bin", "cp0.debug.before.bin", "cp0.debug.armed.bin"}
    for number in range(1, event_count + 1):
        prefix = "event.%02d." % number
        names.add(prefix + "siginfo.bin")
        for side in ("a", "b"):
            for kind in ("regs", "debug", "child.stat", "child.status", "code"):
                names.add(prefix + kind + "." + side + ".bin")
    for number in range(resume_count):
        names.add("resume.%02d.debug.bin" % number)
    return names


def _file_size(name):
    if name == "probe.elf":
        return len(probe_bytes()), True
    if ".regs." in name or name == "cp0.regs.bin":
        return 216, True
    if ".debug." in name:
        return 48, True
    if name.endswith(".siginfo.bin"):
        return 128, True
    if ".code." in name:
        return len(PROBE_CODE), True
    return 4096, False


def _files(transcript, files):
    expected = _expected_files(len(transcript["events"]), len(transcript["resumes"]))
    _keys(files, expected, "two_slot_raw_roster")
    _keys(transcript["raw_files"], expected, "two_slot_binding_roster")
    _need(len(files) <= POLICY["raw_files"], "two_slot_file_count")
    total = 0
    # Check every extent and the complete total before hashing any raw input.
    for name in sorted(expected):
        raw = files[name]
        limit, exact = _file_size(name)
        _need(type(raw) is bytes and 0 < len(raw) <= limit
              and (not exact or len(raw) == limit), "two_slot_raw_size")
        total += len(raw)
        _need(total <= POLICY["raw_total_bytes"], "two_slot_raw_total")
        descriptor = transcript["raw_files"][name]
        _descriptor(descriptor)
        _same(descriptor["size_bytes"], len(raw), "two_slot_file_size_mismatch")
    for name in sorted(expected):
        _same(transcript["raw_files"][name], _binding(files[name]),
              "two_slot_file_binding_mismatch")
    return total


def _stat(raw, process):
    text = raw.decode("ascii")
    match = re.fullmatch(r"([0-9]+) \(([\x20-\x27\x2a-\x7e]{1,64})\) (t) ([0-9 -]+)\n?", text)
    _need(match is not None, "two_slot_process_stat")
    fields = match.group(4).split()
    _need(len(fields) == 49 and all(re.fullmatch(r"-?[0-9]+", part) for part in fields),
          "two_slot_process_stat")
    values = [int(part) for part in fields]
    _need(all(-MAX_INTEGER <= item <= MAX_INTEGER for item in values),
          "two_slot_process_stat")
    _need(int(match.group(1)) == process["child_pid"]
          and values[0] == process["observer_pid"] and values[16] == 1
          and values[18] == process["starttime"], "two_slot_process_identity")
    return match.group(2)


def _text_fields(raw, expected, code):
    text = raw.decode("ascii")
    _need(text.endswith("\n"), code)
    result = {}
    for line in text.splitlines():
        _need(line.count(":") == 1, code)
        key, value = line.split(":", 1)
        _need(key not in result and value.strip(), code)
        result[key] = value.strip()
    _keys(result, expected, code)
    return result


def _status(raw, process, comm):
    value = _text_fields(raw, ("Name", "State", "Tgid", "Pid", "PPid", "TracerPid",
                               "NSpid", "Threads"), "two_slot_process_status")
    _need(value["Name"] == comm and value["State"] == "t (tracing stop)",
          "two_slot_process_status")
    expected = {"Tgid": process["child_pid"], "Pid": process["child_pid"],
                "PPid": process["observer_pid"], "TracerPid": process["observer_pid"],
                "NSpid": process["child_pid"], "Threads": 1}
    for key, number in expected.items():
        _need(re.fullmatch(r"[0-9]+", value[key]) is not None
              and int(value[key]) == number, "two_slot_process_status_identity")


def _identity(files, stat_name, status_name, process):
    comm = _stat(files[stat_name], process)
    _status(files[status_name], process, comm)


def _pidfd(raw, process):
    value = _text_fields(raw, ("pos", "flags", "mnt_id", "ino", "Pid", "NSpid"),
                         "two_slot_pidfd")
    for key in ("pos", "mnt_id", "ino", "Pid", "NSpid"):
        _need(re.fullmatch(r"[0-9]+", value[key]) is not None
              and int(value[key]) <= MAX_INTEGER, "two_slot_pidfd")
    _need(int(value["pos"]) == 0 and int(value["mnt_id"]) > 0 and int(value["ino"]) > 0
          and int(value["Pid"]) == int(value["NSpid"]) == process["child_pid"],
          "two_slot_pidfd_identity")
    _need(re.fullmatch(r"[0-7]+", value["flags"]) is not None
          and int(value["flags"], 8) <= MAX_INTEGER
          and int(value["flags"], 8) & 3 == 2, "two_slot_pidfd_flags")


def _debug(raw, values):
    _same(struct.unpack("<6Q", raw), tuple(values), "two_slot_debug_state")


def _write(value, register, data):
    _keys(value, ("register", "value", "returncode", "errno"), "two_slot_debug_write_fields")
    for key in value:
        _integer(value[key], "two_slot_debug_write_integer")
    _same(value, {"register": register, "value": data, "returncode": 0, "errno": 0},
          "two_slot_debug_write")


def _wait(value, phase, process, status):
    _keys(value, ("phase", "pid", "status", "at_ns"), "two_slot_wait_fields")
    _same(value["phase"], phase, "two_slot_wait_phase")
    _integer(value["pid"], "two_slot_wait_pid", 1, (1 << 31) - 1)
    _integer(value["status"], "two_slot_wait_status", 0, (1 << 32) - 1)
    _integer(value["at_ns"], "two_slot_wait_time")
    _need(value["pid"] == process["child_pid"] and value["status"] == status,
          "two_slot_wait_identity_or_status")
    return value["at_ns"]


def _resume(value, after, files, index, expected_debug):
    _keys(value, ("after", "at_ns", "clear", "request", "address", "signal",
                  "returncode", "errno"), "two_slot_resume_fields")
    _same(value["after"], after, "two_slot_resume_sequence")
    _same(value["request"], "PTRACE_CONT", "two_slot_resume_operation")
    for key in ("at_ns", "address", "signal", "returncode", "errno"):
        _integer(value[key], "two_slot_resume_integer")
    _need(value["address"] == value["signal"] == value["returncode"] == value["errno"] == 0,
          "two_slot_resume_result")
    _write(value["clear"], 6, DR6_RESERVED)
    _debug(files["resume.%02d.debug.bin" % index], expected_debug)
    return value["at_ns"]


def _verify(transcript, files):
    if type(transcript) is bytes:
        _need(0 < len(transcript) <= CONTROL_BYTES, "two_slot_control_size")
        transcript = json.loads(transcript.decode("utf-8"), object_pairs_hook=_pairs,
                                parse_float=_invalid_number, parse_constant=_invalid_number)
    _json_tree(transcript)
    _keys(transcript, ("record_type", "profile", "evidence_origin", "attempt_id", "status",
                       "failure", "process", "options", "timing", "arming", "waits",
                       "resumes", "events", "cleanup", "raw_files", "boundary"),
          "two_slot_transcript_fields")
    for key, expected in (("record_type", RECORD_TYPE), ("profile", PROFILE),
                          ("evidence_origin", "authored_test_fixture")):
        _same(transcript[key], expected, "two_slot_fixture_identity")
    _need(type(transcript["attempt_id"]) is str and
          re.fullmatch(r"[0-9a-f]{32}", transcript["attempt_id"]) is not None,
          "two_slot_attempt_identity")
    _keys(transcript["boundary"], BOUNDARY, "two_slot_boundary_fields")
    for key, expected in BOUNDARY.items():
        _same(transcript["boundary"][key], expected, "two_slot_boundary")
    for key, maximum in (("events", 10), ("resumes", 11), ("waits", 20), ("arming", 4)):
        _need(type(transcript[key]) is list and len(transcript[key]) <= maximum,
              "two_slot_list_bound")
    events, resumes, waits = transcript["events"], transcript["resumes"], transcript["waits"]
    complete = transcript["status"] == "completed"
    _need(type(transcript["status"]) is str and transcript["status"] in ("completed", "incomplete"),
          "two_slot_status")
    if complete:
        _need(len(events) == 10 and transcript["failure"] is None, "two_slot_completed_shape")
        kinds = ["return"] * 9 + ["entry"]
    else:
        kinds = ["return"] * len(events)
        expected_failure = "unexpected_tenth_return" if len(events) == 10 else "stopped_prefix"
        _same(transcript["failure"], expected_failure, "two_slot_incomplete_reason")
    expected_after = ["setup"]
    if events:
        expected_after += ["cp0"] + ["event.%02d" % number for number in range(1, len(events))]
    _need(len(resumes) == len(expected_after), "two_slot_resume_count")
    _need(len(waits) == len(events) + 3 and len(transcript["arming"]) == 4,
          "two_slot_wait_or_arm_count")
    process = transcript["process"]
    _keys(process, ("observer_pid", "child_pid", "starttime", "pidfd"), "two_slot_process_fields")
    for key in ("observer_pid", "child_pid"):
        _integer(process[key], "two_slot_pid", 2, (1 << 31) - 1)
    _need(process["observer_pid"] != process["child_pid"], "two_slot_owned_child")
    _integer(process["starttime"], "two_slot_starttime", 1)
    _integer(process["pidfd"], "two_slot_pidfd_number", 3, (1 << 20) - 1)
    options = transcript["options"]
    _keys(options, ("request", "value", "returncode", "errno"), "two_slot_options_fields")
    _same(options["request"], "PTRACE_SETOPTIONS", "two_slot_options")
    for key in ("value", "returncode", "errno"):
        _integer(options[key], "two_slot_options_integer")
    _same(options, {"request": "PTRACE_SETOPTIONS", "value": PTRACE_OPTIONS,
                    "returncode": 0, "errno": 0}, "two_slot_options")
    timing = transcript["timing"]
    _keys(timing, ("started_ns", "armed_ns", "cleanup_started_ns", "finished_ns"),
          "two_slot_timing_fields")
    for value in timing.values():
        _integer(value, "two_slot_timing_integer")
    started, armed, cleanup_start, finished = (timing[key] for key in
        ("started_ns", "armed_ns", "cleanup_started_ns", "finished_ns"))
    _need(started < armed < cleanup_start <= finished
          and cleanup_start - started <= POLICY["observation_nanoseconds"]
          and finished - cleanup_start <= POLICY["cleanup_nanoseconds"], "two_slot_deadline")
    encoded = _canonical(transcript)
    _need(len(encoded) <= CONTROL_BYTES, "two_slot_control_size")
    raw_total = _files(transcript, files)
    layout = _probe_layout(files["probe.elf"])
    initial_debug = (0, 0, 0, 0, DR6_RESERVED, 0)
    armed_debug = (layout["return"], layout["terminal"], 0, 0, DR6_RESERVED, 5)
    _debug(files["cp0.debug.before.bin"], initial_debug)
    _debug(files["cp0.debug.armed.bin"], armed_debug)
    for write, (register, data) in zip(transcript["arming"],
            ((0, layout["return"]), (1, layout["terminal"]), (6, DR6_RESERVED), (7, 5))):
        _write(write, register, data)
    _identity(files, "child.stat.setup.bin", "child.status.setup.bin", process)
    _identity(files, "cp0.child.stat.bin", "cp0.child.status.bin", process)
    _pidfd(files["child.pidfd.info.bin"], process)
    cp0_registers = struct.unpack("<27Q", files["cp0.regs.bin"])
    _need(cp0_registers[16] == layout["entry"], "two_slot_cp0_rip")
    # TF requests architectural single stepping even when the ptrace operation
    # is CONT. RF behavior across actual hardware stops/resumes is not qualified
    # by these authored snapshots; no guessed live RF value is required here.
    _need(cp0_registers[18] & 0x100 == 0, "two_slot_single_step_flag")
    setup_time = _wait(waits[0], "setup", process, 0x137F)
    exec_time = _wait(waits[1], "exec", process, 0x4057F)
    resume_times = [_resume(row, after, files, number,
                           initial_debug if number == 0 else armed_debug)
                    for number, (row, after) in enumerate(zip(resumes, expected_after))]
    _need(started <= setup_time < resume_times[0] < exec_time < armed,
          "two_slot_setup_order")
    if events:
        _need(armed < resume_times[1], "two_slot_first_resume_order")
    last_sample_time = armed
    for number, (event, kind) in enumerate(zip(events, kinds), 1):
        _keys(event, ("index", "kind", "sample_times_ns"), "two_slot_event_fields")
        _integer(event["index"], "two_slot_event_index", 1, 10)
        _need(event["index"] == number and event["kind"] == kind
              and type(event["kind"]) is str, "two_slot_event_sequence")
        samples = event["sample_times_ns"]
        _need(type(samples) is list and len(samples) == 2, "two_slot_sample_times")
        for value in samples:
            _integer(value, "two_slot_sample_time")
        stop_time = _wait(waits[number + 1], "event.%02d" % number, process, 0x57F)
        _need(resume_times[number] < stop_time <= samples[0] < samples[1] < cleanup_start,
              "two_slot_event_time_order")
        if number < len(events):
            _need(samples[1] < resume_times[number + 1], "two_slot_resume_after_samples")
        last_sample_time = samples[1]
        prefix = "event.%02d." % number
        target = layout["return"] if kind == "return" else layout["terminal"]
        hit_debug = (layout["return"], layout["terminal"], 0, 0,
                     DR6_RESERVED | (1 if kind == "return" else 2), 5)
        for field in ("regs", "debug", "child.stat", "child.status", "code"):
            _same(files[prefix + field + ".a.bin"], files[prefix + field + ".b.bin"],
                  "two_slot_unstable_samples")
        for side in ("a", "b"):
            regs = struct.unpack("<27Q", files[prefix + "regs." + side + ".bin"])
            _need(regs[16] == target, "two_slot_event_rip")
            _need(regs[18] & 0x100 == 0, "two_slot_single_step_flag")
            if complete or number <= 9:
                _need(regs[11] == (10 - number if kind == "return" else 0),
                      "two_slot_probe_loop_state")
            _debug(files[prefix + "debug." + side + ".bin"], hit_debug)
            _identity(files, prefix + "child.stat." + side + ".bin",
                      prefix + "child.status." + side + ".bin", process)
            _same(files[prefix + "code." + side + ".bin"], layout["code"],
                  "two_slot_probe_code_changed")
        siginfo = files[prefix + "siginfo.bin"]
        expected_siginfo = bytearray(128)
        struct.pack_into("<iii", expected_siginfo, 0, 5, 0, 4)
        struct.pack_into("<Q", expected_siginfo, 16, target)
        _same(siginfo, bytes(expected_siginfo), "two_slot_siginfo_cause")
    cleanup = transcript["cleanup"]
    _keys(cleanup, ("signal", "method", "pidfd", "pid", "at_ns", "returncode", "errno", "reaped"),
          "two_slot_cleanup_fields")
    for key in ("signal", "pidfd", "pid", "at_ns", "returncode", "errno"):
        _integer(cleanup[key], "two_slot_cleanup_integer")
    _need(cleanup["signal"] == 9 and cleanup["method"] == "pidfd_send_signal"
          and type(cleanup["method"]) is str and cleanup["pidfd"] == process["pidfd"]
          and cleanup["pid"] == process["child_pid"]
          and cleanup["returncode"] == cleanup["errno"] == 0
          and cleanup["reaped"] is True, "two_slot_owned_cleanup")
    reap_time = _wait(waits[-1], "reap", process, 9)
    _need(last_sample_time < cleanup_start <= cleanup["at_ns"] < reap_time <= finished,
          "two_slot_cleanup_order")
    return {
        "record_type": "required_gate_idempotence_loader_two_slot_fixture_verification_v0",
        "profile": PROFILE,
        "evidence_origin": "authored_test_fixture",
        "status": "accepted" if complete else "incomplete",
        "fixture_structure_and_mechanics_verified": True,
        "complete_fixture_sequence_verified": complete,
        "preserved_return_events": sum(kind == "return" for kind in kinds),
        "accepted_fixture_return_events": min(sum(kind == "return" for kind in kinds), 9),
        "unexpected_tenth_return_preserved": not complete and len(events) == 10,
        "ptrace_cont_count": len(resumes),
        "post_entry_resumes": 0,
        "owned_cleanup_fixture_verified": True,
        "probe": _binding(files["probe.elf"]),
        "transcript": _binding(encoded),
        "raw_file_count": len(files),
        "raw_total_bytes": raw_total,
        **BOUNDARY,
    }


def verify_transcript(*, transcript, files):
    """Validate a closed authored fixture, never return a live qualification.

    ``transcript`` is a strictly typed dict or bounded UTF-8 JSON bytes.
    ``files`` is an exact mapping from the recorded names to external raw bytes.
    Incomplete prefixes require owned cleanup and return status ``incomplete``.
    """
    try:
        return _verify(transcript, files)
    except TwoSlotError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, UnicodeError, struct.error,
            OverflowError, RecursionError) as exc:
        raise TwoSlotError("two_slot_invalid") from exc
