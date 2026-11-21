#!/usr/bin/env python3
"""Reconstruct a bounded two-slot probe record without running a native probe.

A reconstructed native-origin record is evidence about its selected recorded
context. It neither authenticates physical execution nor admits the current
host or an original-loader acquisition. Scripted backend records retain their
different origin and cannot become native qualification by passing mechanics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_loader_two_slot_v0 as fixture

ROOT = Path(__file__).resolve().parents[1]
RECORD_TYPE = "required_gate_idempotence_loader_two_slot_qualification_v0"
PROFILE = "linux_x86_64_loader_two_slot_qualification_v0"
SCHEMA_PATH = "schemas/required_gate_idempotence_loader_two_slot_qualification_v0.schema.json"
SOURCE_PATHS = tuple(sorted((
    SCHEMA_PATH,
    "tools/check_required_gate_idempotence_loader_two_slot_qualification_v0.py",
    "tools/qualify_required_gate_idempotence_loader_two_slot_v0.py",
    "tools/required_gate_idempotence_loader_two_slot_v0.py",
)))
MAX_RECORD_BYTES = 1024 * 1024
MAX_RAW_BYTES = 262144
MAX_RAW_FILES = 160
PROC_BYTES = 65536
MAX_OPERATIONS = 128
MAX_INTEGER = (1 << 63) - 1
DR6_RESERVED = 0xFFFF0FF0
PTRACE_OPTIONS = 0x10001E
PROBE_ENTRY = 0x400080
SLOT0_TARGET = 0x400085
SLOT1_TARGET = 0x400088
PROBE_CODE = bytes.fromhex("b90900000090e2fd0f0b")
NAMESPACE_NAMES = ("cgroup", "ipc", "mnt", "net", "pid", "pid_for_children",
                   "time", "time_for_children", "user", "uts")
BOUNDARY = {
    "original_native_acquisition_performed": False,
    "original_acquisition_ready": False,
    "source_build_gate_satisfied": False,
    "b2_complete": False,
    "consumer_resolution_observed": False,
    "physical_execution_authenticated": False,
    "current_host_admission_satisfied": False,
    "metric_pass": None,
    "authority_effect": "none",
}


class QualificationError(ValueError):
    """Stable rejection without raw process data or filesystem details."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise QualificationError(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def binding(raw):
    _need(type(raw) is bytes, "two_slot_qualification_binding_type")
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def probe_bytes():
    """Construct the existing fixed authored probe; never execute it."""
    raw = fixture.probe_bytes()
    _need(len(raw) == 138 and raw[128:] == PROBE_CODE,
          "two_slot_qualification_probe_definition")
    return raw


def _same(actual, expected, code):
    _need(canonical(actual) == canonical(expected), code)


def _digest(value, code):
    _need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, code)


def _keys(value, expected, code):
    _need(type(value) is dict and set(value) == set(expected), code)


def _integer(value, code, minimum=0, maximum=MAX_INTEGER):
    _need(type(value) is int and minimum <= value <= maximum, code)
    return value


def _read_regular(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        _need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit,
              "two_slot_qualification_file_extent")
        chunks, size = [], 0
        while True:
            part = os.read(fd, min(65536, limit + 1 - size))
            if not part:
                break
            chunks.append(part)
            size += len(part)
            _need(size <= limit, "two_slot_qualification_file_extent")
        after = os.fstat(fd)
        selected = lambda value: (value.st_dev, value.st_ino, value.st_mode,
                                  value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        _need(selected(before) == selected(after) and size == before.st_size,
              "two_slot_qualification_file_changed")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _source_bytes():
    return {path: _read_regular(ROOT / path, MAX_RECORD_BYTES) for path in SOURCE_PATHS}


def source_inventory():
    """Fresh exact implementation inventory, with no authored-record recursion."""
    return [{"path": path, **binding(raw)} for path, raw in _source_bytes().items()]


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        _need(key not in value, "two_slot_qualification_duplicate_key")
        value[key] = item
    return value


def _number(_value):
    raise QualificationError("two_slot_qualification_noninteger_json")


def _tree(value):
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        _need(count <= 12000 and depth <= 12, "two_slot_qualification_json_structure")
        if type(item) is dict:
            _need(len(item) <= MAX_RAW_FILES, "two_slot_qualification_json_structure")
            for key, child in item.items():
                _need(type(key) is str and len(key) <= 128,
                      "two_slot_qualification_json_key")
                pending.append((child, depth + 1))
        elif type(item) is list:
            _need(len(item) <= MAX_RAW_FILES, "two_slot_qualification_json_structure")
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            _need(len(item) <= PROC_BYTES * 2, "two_slot_qualification_json_string")
        else:
            _need(item is None or type(item) is bool or
                  (type(item) is int and -MAX_INTEGER <= item <= MAX_INTEGER),
                  "two_slot_qualification_json_value")


def parse(raw, limit=MAX_RECORD_BYTES):
    _need(type(raw) is bytes and 0 < len(raw) <= limit,
          "two_slot_qualification_record_extent")
    try:
        value = json.loads(raw.decode("ascii"), object_pairs_hook=_pairs,
                           parse_float=_number, parse_constant=_number)
        _tree(value)
        return value
    except QualificationError:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise QualificationError("two_slot_qualification_invalid_json") from exc


def validate_context(value):
    _keys(value, ("uname", "boot_id", "observer", "namespaces"),
          "two_slot_qualification_context_fields")
    _keys(value["uname"], ("sysname", "release", "version", "machine"),
          "two_slot_qualification_uname_fields")
    for text in value["uname"].values():
        _need(type(text) is str and 0 < len(text) <= 256
              and all(32 <= ord(char) <= 126 for char in text),
              "two_slot_qualification_uname")
    _need(value["uname"]["sysname"] == "Linux" and value["uname"]["machine"] == "x86_64",
          "two_slot_qualification_platform")
    _need(type(value["boot_id"]) is str and re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", value["boot_id"]),
          "two_slot_qualification_boot_identity")
    _keys(value["observer"], ("size_bytes", "sha256"),
          "two_slot_qualification_observer_descriptor")
    _integer(value["observer"]["size_bytes"], "two_slot_qualification_observer_size", 1, 64 * 1024 * 1024)
    _digest(value["observer"]["sha256"], "two_slot_qualification_observer_digest")
    namespaces = value["namespaces"]
    _keys(namespaces, NAMESPACE_NAMES, "two_slot_qualification_namespace_fields")
    _need((namespaces["time"] is None) == (namespaces["time_for_children"] is None),
          "two_slot_qualification_time_namespace_pair")
    for name, link in namespaces.items():
        if name in ("time", "time_for_children") and link is None:
            continue
        prefix = name.removesuffix("_for_children")
        _need(type(link) is str and len(link) <= 128 and
              re.fullmatch(re.escape(prefix) + r":\[[1-9][0-9]*\]", link),
              "two_slot_qualification_namespace_identity")
    return value


def complete_raw_names():
    names = {"probe.elf", "probe.seals.bin", "probe.mode.bin",
             "observer.stat.bin", "observer.status.bin", "child.pidfd.info.bin",
             "child.stat.setup.bin", "child.status.setup.bin", "setup.debug.before.bin",
             "cp0.child.stat.bin", "cp0.child.status.bin", "cp0.regs.bin", "cp0.auxv.bin",
             "cp0.executable.elf", "cp0.debug.before.bin", "cp0.debug.armed.bin"}
    for number in range(11):
        names.add("resume.%02d.debug.bin" % number)
    for number in range(1, 11):
        prefix = "event.%02d." % number
        names.add(prefix + "siginfo.bin")
        for side in ("a", "b"):
            for kind in ("regs", "debug", "child.stat", "child.status", "code"):
                names.add(prefix + kind + "." + side + ".bin")
    return names


INCOMPLETE_EXTRA_RAW = {"unexpected.event_message.bin", "unexpected.regs.bin",
                      "unexpected.debug.bin", "unexpected.siginfo.bin"}


def raw_limit(name):
    if name in ("probe.elf", "cp0.executable.elf"):
        return 138, True
    if name in ("probe.seals.bin", "probe.mode.bin", "unexpected.event_message.bin"):
        return 8, True
    if ".regs." in name:
        return 216, True
    if ".debug." in name:
        return 48, True
    if ".siginfo." in name:
        return 128, True
    if ".code." in name:
        return 10, True
    return PROC_BYTES, False


def _raw(record):
    rows = record["raw"]
    _need(type(rows) is dict and len(rows) <= MAX_RAW_FILES,
          "two_slot_qualification_raw_count")
    allowed = complete_raw_names() | INCOMPLETE_EXTRA_RAW
    _need(set(rows) <= allowed, "two_slot_qualification_raw_roster")
    if record["status"] == "completed":
        _need(set(rows) == complete_raw_names(), "two_slot_qualification_completed_raw_roster")
    total = 0
    # Validate every encoded extent and aggregate before decoding or hashing any payload.
    for name, descriptor in rows.items():
        _keys(descriptor, ("size_bytes", "sha256", "hex"),
              "two_slot_qualification_raw_descriptor")
        limit, exact = raw_limit(name)
        size = _integer(descriptor["size_bytes"], "two_slot_qualification_raw_size", 1, limit)
        # A failed read can leave a nonempty short diagnostic field. Preserve
        # that bounded raw observation in an incomplete record without claiming
        # it satisfies the complete ABI or mechanics predicates.
        _need(record["status"] != "completed" or not exact or size == limit,
              "two_slot_qualification_raw_size")
        encoded = descriptor["hex"]
        _need(type(encoded) is str and len(encoded) == size * 2
              and re.fullmatch(r"[0-9a-f]+", encoded), "two_slot_qualification_raw_encoding")
        _digest(descriptor["sha256"], "two_slot_qualification_raw_digest")
        total += size
        _need(total <= MAX_RAW_BYTES, "two_slot_qualification_raw_total")
    files = {}
    for name, descriptor in rows.items():
        raw = bytes.fromhex(descriptor["hex"])
        _same(binding(raw), {key: descriptor[key] for key in ("size_bytes", "sha256")},
              "two_slot_qualification_raw_binding")
        files[name] = raw
    return files, total


def _proc_stat(raw):
    text = raw.decode("ascii")
    split = text.rfind(") ")
    _need(split > 0 and " (" in text[:split], "two_slot_qualification_proc_stat")
    pid_text, comm = text[:split].split(" (", 1)
    rest = text[split + 2:].split()
    _need(re.fullmatch(r"[1-9][0-9]*", pid_text) and 0 < len(comm) <= 64
          and all(32 <= ord(char) <= 126 for char in comm) and len(rest) == 50
          and len(rest[0]) == 1, "two_slot_qualification_proc_stat")
    _need(all(re.fullmatch(r"-?[0-9]+", field) for field in rest[1:]),
          "two_slot_qualification_proc_stat")
    values = [int(field) for field in rest[1:]]
    # proc stat mixes signed and unsigned kernel fields. In particular rsslim
    # can legitimately be ULONG_MAX; only selected identity fields below use
    # the narrower PID/start-time bounds.
    _need(all(-(1 << 63) <= item <= (1 << 64) - 1 for item in values),
          "two_slot_qualification_proc_stat")
    _need(2 <= int(pid_text) <= (1 << 31) - 1
          and 0 <= values[0] <= (1 << 31) - 1
          and 1 <= values[16] <= (1 << 31) - 1
          and 1 <= values[18] <= MAX_INTEGER,
          "two_slot_qualification_proc_stat_identity_extent")
    return {"pid": int(pid_text), "comm": comm, "state": rest[0],
            "ppid": values[0], "threads": values[16], "starttime": values[18]}


def _text_fields(raw):
    text = raw.decode("ascii")
    _need(text.endswith("\n") and "\x00" not in text,
          "two_slot_qualification_proc_text")
    fields = {}
    for line in text.splitlines():
        _need(":" in line, "two_slot_qualification_proc_text")
        key, value = line.split(":", 1)
        _need(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", key) and key not in fields,
              "two_slot_qualification_proc_duplicate_or_key")
        fields[key] = value.strip()
    return fields


def _status(raw, expected, comm, *, stopped):
    fields = _text_fields(raw)
    _need(set(("Name", "State", "Tgid", "Pid", "PPid", "TracerPid", "NSpid", "Threads")) <= set(fields),
          "two_slot_qualification_proc_status_fields")
    _need(fields["Name"] == comm and
          (fields["State"] == "t (tracing stop)" if stopped else bool(fields["State"])),
          "two_slot_qualification_proc_status")
    for key, wanted in expected.items():
        _need(re.fullmatch(r"[0-9]+", fields[key]) and int(fields[key]) == wanted,
              "two_slot_qualification_proc_status_identity")


def _child_identity(files, stat_name, status_name, process):
    value = _proc_stat(files[stat_name])
    _need(value["pid"] == process["child_pid"] and value["ppid"] == process["observer_pid"]
          and value["starttime"] == process["starttime"] and value["threads"] == 1
          and value["state"] == "t", "two_slot_qualification_child_identity")
    _status(files[status_name], {"Tgid": process["child_pid"], "Pid": process["child_pid"],
            "PPid": process["observer_pid"], "TracerPid": process["observer_pid"],
            "NSpid": process["child_pid"], "Threads": 1}, value["comm"], stopped=True)


def _observer(files, process):
    value = _proc_stat(files["observer.stat.bin"])
    _need(value["pid"] == process["observer_pid"] and value["threads"] == 1
          and value["starttime"] > 0, "two_slot_qualification_observer_identity")
    _status(files["observer.status.bin"], {"Tgid": process["observer_pid"],
            "Pid": process["observer_pid"], "PPid": value["ppid"], "TracerPid": 0,
            "NSpid": process["observer_pid"], "Threads": 1}, value["comm"], stopped=False)


def _pidfd(raw, process):
    fields = _text_fields(raw)
    _need(set(("pos", "flags", "mnt_id", "ino", "Pid", "NSpid")) <= set(fields),
          "two_slot_qualification_pidfd_fields")
    for key in ("pos", "mnt_id", "ino", "Pid", "NSpid"):
        _need(re.fullmatch(r"[0-9]+", fields[key]) and int(fields[key]) <= MAX_INTEGER,
              "two_slot_qualification_pidfd_value")
    _need(int(fields["pos"]) == 0 and int(fields["mnt_id"]) > 0 and int(fields["ino"]) > 0
          and int(fields["Pid"]) == int(fields["NSpid"]) == process["child_pid"],
          "two_slot_qualification_pidfd_identity")
    _need(re.fullmatch(r"[0-7]+", fields["flags"])
          and int(fields["flags"], 8) <= MAX_INTEGER and int(fields["flags"], 8) & 3 == 2,
          "two_slot_qualification_pidfd_flags")


def _auxv(raw):
    _need(0 < len(raw) <= PROC_BYTES and len(raw) % 16 == 0,
          "two_slot_qualification_auxv_extent")
    pairs = list(struct.iter_unpack("<QQ", raw))
    _need(pairs[-1] == (0, 0) and all(key != 0 for key, _ in pairs[:-1]),
          "two_slot_qualification_auxv_terminator")
    result = {}
    for key, value in pairs[:-1]:
        _need(key not in result, "two_slot_qualification_auxv_duplicate")
        result[key] = value
    expected = {3: 0x400040, 4: 56, 5: 1, 6: 4096, 7: 0, 9: PROBE_ENTRY}
    _need(all(result.get(key) == value for key, value in expected.items()),
          "two_slot_qualification_auxv_identity")


def _debug(raw, expected):
    _need(struct.unpack("<6Q", raw) == tuple(expected), "two_slot_qualification_debug_state")


def _registers(raw, *, target, count=None, hardware=False):
    values = struct.unpack("<27Q", raw)
    _need(values[16] == target and values[18] & 0x100 == 0,
          "two_slot_qualification_register_state")
    if hardware:
        _need(values[18] & 0x10000 != 0, "two_slot_qualification_resume_flag")
    if count is not None:
        _need(values[11] == count, "two_slot_qualification_loop_progress")


def _journal(record):
    started, finished = record["timing"]["started_ns"], record["timing"]["finished_ns"]
    prior = started
    for row in record["operations"]:
        _need(prior <= row["at_ns"] <= finished, "two_slot_qualification_operation_time")
        prior = row["at_ns"]
    _need(started <= finished, "two_slot_qualification_timing_order")


def _completed(record, files):
    process, timing = record["process"], record["timing"]
    _need(record["failure"] is None and record["phase"] == "finished",
          "two_slot_qualification_completed_status")
    for key in ("observer_pid", "child_pid"):
        _integer(process[key], "two_slot_qualification_process_pid", 2, (1 << 31) - 1)
    _need(process["observer_pid"] != process["child_pid"] and process["proc_dir_pinned"] is True
          and process["unexpected_children"] == [], "two_slot_qualification_owned_process")
    _integer(process["starttime"], "two_slot_qualification_process_start", 1)
    _integer(process["pidfd"], "two_slot_qualification_process_pidfd", 3, (1 << 20) - 1)
    started, cleanup, finished = (timing[key] for key in
        ("started_ns", "cleanup_started_ns", "finished_ns"))
    _integer(cleanup, "two_slot_qualification_cleanup_time")
    _need(started < cleanup < finished and cleanup - started <= 15_000_000_000
          and finished - cleanup <= 2_000_000_000, "two_slot_qualification_deadline")
    expected_probe = probe_bytes()
    _same(record["probe"], {**binding(expected_probe), "seals": 15, "mode": 320},
          "two_slot_qualification_probe_descriptor")
    _need(files["probe.elf"] == files["cp0.executable.elf"] == expected_probe,
          "two_slot_qualification_original_probe_bytes")
    _need(struct.unpack("<Q", files["probe.seals.bin"])[0] == 15
          and struct.unpack("<Q", files["probe.mode.bin"])[0] == 320,
          "two_slot_qualification_probe_seals_or_mode")
    _observer(files, process)
    _child_identity(files, "child.stat.setup.bin", "child.status.setup.bin", process)
    _child_identity(files, "cp0.child.stat.bin", "cp0.child.status.bin", process)
    _pidfd(files["child.pidfd.info.bin"], process)
    _auxv(files["cp0.auxv.bin"])
    _registers(files["cp0.regs.bin"], target=PROBE_ENTRY)
    initial = (0, 0, 0, 0, DR6_RESERVED, 0)
    armed = (SLOT0_TARGET, SLOT1_TARGET, 0, 0, DR6_RESERVED, 5)
    _debug(files["setup.debug.before.bin"], initial)
    _debug(files["cp0.debug.before.bin"], initial)
    _debug(files["cp0.debug.armed.bin"], armed)
    operations = iter(record["operations"])
    last_time = started

    def take(expected):
        nonlocal last_time
        row = next(operations, None)
        _need(row is not None, "two_slot_qualification_operation_missing")
        _same({key: value for key, value in row.items() if key != "at_ns"}, expected,
              "two_slot_qualification_operation_sequence")
        _need(last_time <= row["at_ns"], "two_slot_qualification_operation_order")
        last_time = row["at_ns"]
        return last_time

    def wait(phase, status):
        return take({"op": "wait", "phase": phase, "pid": process["child_pid"], "status": status})

    def write(phase, register, value):
        return take({"op": "debug_write", "phase": phase, "register": register,
                     "value": value, "returncode": 0, "errno": 0})

    def resume(number, after, debug):
        write("resume.%02d" % number, 6, DR6_RESERVED)
        _debug(files["resume.%02d.debug.bin" % number], debug)
        return take({"op": "continue", "after": after, "address": 0, "signal": 0,
                     "returncode": 0, "errno": 0})

    wait("setup", 0x137F)
    take({"op": "options", "value": PTRACE_OPTIONS, "returncode": 0, "errno": 0})
    resume(0, "setup", initial)
    wait("exec", 0x4057F)
    for register, value in ((0, SLOT0_TARGET), (1, SLOT1_TARGET), (6, DR6_RESERVED), (7, 5)):
        write("arming", register, value)
    resume(1, "cp0", armed)
    for number in range(1, 11):
        phase = "event.%02d" % number
        wait(phase, 0x57F)
        target = SLOT0_TARGET if number <= 9 else SLOT1_TARGET
        count = 10 - number
        hit = (SLOT0_TARGET, SLOT1_TARGET, 0, 0,
               DR6_RESERVED | (1 if number <= 9 else 2), 5)
        prefix = phase + "."
        siginfo = files[prefix + "siginfo.bin"]
        _need(struct.unpack_from("<iii", siginfo)[0:3] == (5, 0, 4)
              and struct.unpack_from("<Q", siginfo, 16)[0] == target,
              "two_slot_qualification_trap_cause")
        # Kernel siginfo padding is not part of the selected identity/cause.
        for kind in ("regs", "debug", "code"):
            _need(files[prefix + kind + ".a.bin"] == files[prefix + kind + ".b.bin"],
                  "two_slot_qualification_unstable_samples")
        sample_times = []
        for side in ("a", "b"):
            sample_times.append(take({"op": "sample", "phase": phase, "side": side}))
            _registers(files[prefix + "regs." + side + ".bin"], target=target,
                       count=count, hardware=True)
            _debug(files[prefix + "debug." + side + ".bin"], hit)
            _child_identity(files, prefix + "child.stat." + side + ".bin",
                            prefix + "child.status." + side + ".bin", process)
            _need(files[prefix + "code." + side + ".bin"] == PROBE_CODE,
                  "two_slot_qualification_live_code")
        _need(sample_times[0] < sample_times[1] < cleanup,
              "two_slot_qualification_sample_times")
        if number <= 9:
            resume(number + 1, phase, armed)
    _need(last_time < cleanup, "two_slot_qualification_cleanup_start")
    kill_time = take({"op": "kill", "method": "pidfd_send_signal", "pid": process["child_pid"],
                     "pidfd": process["pidfd"], "signal": 9, "returncode": 0, "errno": 0})
    reap_time = wait("reap", 9)
    _need(cleanup <= kill_time < reap_time <= finished,
          "two_slot_qualification_cleanup_sequence")
    _need(next(operations, None) is None, "two_slot_qualification_extra_operation")


def _schema(record, schema_bytes):
    import jsonschema
    schema = parse(schema_bytes)
    validator = jsonschema.Draft202012Validator(schema)
    _need(next(validator.iter_errors(record), None) is None,
          "two_slot_qualification_schema")


def verify_record(*, record_bytes, expected_record_sha256, expected_context):
    """Verify selected bytes and reconstruct complete mechanics, never run a probe.

    An incomplete record can preserve deliberately failed raw observations. Its
    report does not claim that the incomplete prefix meets complete predicates.
    """
    try:
        _need(type(record_bytes) is bytes and 0 < len(record_bytes) <= MAX_RECORD_BYTES,
              "two_slot_qualification_record_extent")
        _digest(expected_record_sha256, "two_slot_qualification_record_digest")
        _need(hashlib.sha256(record_bytes).hexdigest() == expected_record_sha256,
              "two_slot_qualification_record_digest_mismatch")
        validate_context(expected_context)
        sources_before = _source_bytes()
        inventory = [{"path": path, **binding(raw)} for path, raw in sources_before.items()]
        record = parse(record_bytes)
        _schema(record, sources_before[SCHEMA_PATH])
        _same(record["boundary"], BOUNDARY, "two_slot_qualification_boundary")
        files, total = _raw(record)
        _journal(record)
        complete = record["status"] == "completed"
        context_matches = record["context"] == expected_context
        source_matches = record["sources"] == inventory
        if record["context"] is not None:
            validate_context(record["context"])
        if record["context_after"] is not None:
            validate_context(record["context_after"])
        if complete:
            _need(context_matches and record["context_after"] == expected_context,
                  "two_slot_qualification_selected_context")
            _need(source_matches and record["sources_after"] == inventory,
                  "two_slot_qualification_selected_sources")
            _completed(record, files)
        else:
            _need(record["failure"] is not None, "two_slot_qualification_incomplete_reason")
        _need(_source_bytes() == sources_before, "two_slot_qualification_sources_changed")
        native = complete and record["evidence_origin"] == "native_owned_probe"
        scripted = complete and record["evidence_origin"] == "scripted_test_backend"
        status = ("accepted_native_qualification_record" if native else
                  "accepted_scripted_qualification_record" if scripted else "preserved_incomplete")
        return {
            "record_type": "required_gate_idempotence_loader_two_slot_qualification_verification_v0",
            "profile": PROFILE,
            "status": status,
            "evidence_origin": record["evidence_origin"],
            "record": binding(record_bytes),
            "selected_context": binding(canonical(expected_context)),
            "record_binding_verified": True,
            "selected_context_binding_verified": context_matches,
            "source_inventory_verified": source_matches and record["sources_after"] == inventory,
            "complete_mechanics_verified": complete,
            "native_record_reconstructed": native,
            "scripted_record_reconstructed": scripted,
            "incomplete_record_preserved": not complete,
            "raw_file_count": len(files), "raw_total_bytes": total,
            "ptrace_cont_count": sum(row["op"] == "continue" and row["returncode"] == 0
                                      for row in record["operations"]),
            "accepted_return_events": 9 if complete else 0,
            "post_terminal_resumes": 0 if complete else None,
            **BOUNDARY,
        }
    except QualificationError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, UnicodeError, struct.error,
            OSError, OverflowError, RecursionError) as exc:
        raise QualificationError("two_slot_qualification_invalid") from exc


def _write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    try:
        owned = os.fstat(fd)
        _need(stat.S_ISREG(owned.st_mode) and owned.st_nlink == 1,
              "two_slot_qualification_output_identity")
        current = os.stat(path, follow_symlinks=False)
        _need((current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino),
              "two_slot_qualification_output_replaced")
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            _need(count > 0, "two_slot_qualification_output_write")
            view = view[count:]
        os.fsync(fd)
        current = os.stat(path, follow_symlinks=False)
        _need((current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino),
              "two_slot_qualification_output_replaced")
    except BaseException:
        # Failure after a complete write (including fsync failure) must not leave
        # an accepted report in our new inode. Touch only the owned descriptor:
        # a concurrently replaced pathname is another file and must survive.
        try:
            os.ftruncate(fd, 0)
        except OSError:
            pass
        raise
    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--record-sha256", required=True)
    parser.add_argument("--expected-context", type=Path, required=True)
    parser.add_argument("--expected-context-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        context_raw = _read_regular(args.expected_context, 16384)
        _digest(args.expected_context_sha256, "two_slot_qualification_context_digest")
        _need(binding(context_raw)["sha256"] == args.expected_context_sha256,
              "two_slot_qualification_context_digest_mismatch")
        report = verify_record(record_bytes=_read_regular(args.record, MAX_RECORD_BYTES),
            expected_record_sha256=args.record_sha256, expected_context=parse(context_raw, 16384))
        _write_new(args.output, canonical(report))
        return 0 if report["complete_mechanics_verified"] else 1
    except (OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, QualificationError) else "two_slot_qualification_io"
        sys.stderr.write(code + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
