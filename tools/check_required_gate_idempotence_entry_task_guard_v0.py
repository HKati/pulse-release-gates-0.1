"""Byte-only checks for the selected entry observation's child task guard.

This module never imports its installer or installs a filter. Installation
evidence is a source-bound pre-exec observer transcript plus kernel procfs
snapshots, not privileged kernel filter readback or physical authentication.
The guard only excludes selected task-creation routes; it is not containment.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import stat
import struct

PROFILE = "linux_x86_64_entry_task_guard_v0"
INSTALLATION_TYPE = "required_gate_idempotence_entry_task_guard_installation_v0"
QUALIFICATION_TYPE = "required_gate_idempotence_entry_task_guard_qualification_v0"
AUDIT_ARCH_X86_64 = 0xC000003E
X32_SYSCALL_BIT = 0x40000000
KILL_PROCESS, ALLOW = 0x80000000, 0x7FFF0000
BLOCKED_SYSCALLS = {"clone": 56, "fork": 57, "vfork": 58,
                    "io_uring_setup": 425, "io_uring_enter": 426,
                    "io_uring_register": 427, "clone3": 435}
# Independently pinned little-endian sock_filter bytes. The installer builds
# its own rows and must match these bytes before making either prctl call.
PROGRAM_BYTES = bytes.fromhex(
    "2000000004000000150001003e0000c006000000000000802000000000000000"
    "4500000100000040060000000000008015000001380000000600000000000080"
    "15000001390000000600000000000080150000013a0000000600000000000080"
    "15000001a9010000060000000000008015000001aa0100000600000000000080"
    "15000001ab010000060000000000008015000001b30100000600000000000080"
    "060000000000ff7f")
PROGRAM_INSTRUCTION_COUNT = 21
SOURCE_PATHS = (
    "tools/check_required_gate_idempotence_entry_task_guard_v0.py",
    "tools/required_gate_idempotence_entry_task_guard_v0.py",
)
NAMESPACE_NAMES = ("cgroup", "ipc", "mnt", "net", "pid", "pid_for_children",
                   "time", "time_for_children", "user", "uts")
MAX_INSTALLATION_BYTES = 16384
MAX_QUALIFICATION_BYTES = 512 * 1024
PROC_BYTES = 65536
MAX_FDS = 8
FULL_SEALS = 15
QUALIFICATION_CASES = (*BLOCKED_SYSCALLS, "x32_getpid", "compat_getpid",
                       "native_getpid", "exec_survival_clone")
QUALIFICATION_LIMITS = {"wall_seconds": 30, "case_seconds": 2,
                        "cleanup_seconds": 2, "cases": 11,
                        "stdout_bytes": 4096, "stderr_bytes": 4096,
                        "total_record_bytes": MAX_QUALIFICATION_BYTES}
BOUNDARY = {"original_native_acquisition_performed": False,
            "hosted_environment_qualified": False,
            "physical_authentication": False,
            "privileged_filter_readback": False,
            "containment_qualification_claimed": False,
            "execution_authorized": False, "diagnostic_only": True,
            "metric_pass": None, "authority_effect": "none"}
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class TaskGuardError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(value, code):
    if not value:
        raise TaskGuardError(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def binding(raw):
    _need(type(raw) is bytes, "entry_guard_binding_bytes")
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def program_binding():
    return binding(PROGRAM_BYTES)


def _keys(value, names, code):
    _need(type(value) is dict and set(value) == set(names), code)


def _same(value, expected, code):
    _need(canonical(value) == canonical(expected), code)


def _integer(value, code, minimum=0, maximum=(1 << 64) - 1):
    _need(type(value) is int and minimum <= value <= maximum, code)
    return value


def _pairs(items):
    result = {}
    for key, value in items:
        _need(key not in result, "entry_guard_duplicate_json_key")
        result[key] = value
    return result


def _number(_):
    raise TaskGuardError("entry_guard_noninteger_json")


def strict(raw, limit=MAX_INSTALLATION_BYTES):
    _need(type(raw) is bytes and 0 < len(raw) <= limit, "entry_guard_json_size")
    try:
        value = json.loads(raw.decode("ascii"), object_pairs_hook=_pairs,
                           parse_float=_number, parse_constant=_number)
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, TaskGuardError):
            raise
        raise TaskGuardError("entry_guard_json_invalid") from exc
    _same(raw.decode("ascii"), canonical(value).decode("ascii"),
          "entry_guard_json_not_canonical")
    return value


def _text_bytes(value, code, maximum=PROC_BYTES):
    _need(type(value) is str, code)
    try:
        raw = value.encode("ascii")
    except UnicodeError as exc:
        raise TaskGuardError(code) from exc
    _need(0 < len(raw) <= maximum and b"\0" not in raw, code)
    return raw


def parse_status(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= PROC_BYTES, "entry_guard_status_size")
    try:
        fields = {}
        for line in raw.decode("ascii").splitlines():
            name, value = line.split(":", 1)
            _need(name not in fields, "entry_guard_status_duplicate")
            fields[name] = value.strip()
        names = ("Pid", "Tgid", "PPid", "TracerPid", "Threads", "NoNewPrivs",
                 "Seccomp", "Seccomp_filters")
        _need(all(name in fields and re.fullmatch(r"[0-9]+", fields[name])
                  for name in names), "entry_guard_status_fields")
        return {name: int(fields[name]) for name in names}
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, TaskGuardError):
            raise
        raise TaskGuardError("entry_guard_status_invalid") from exc


def parse_stat(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= PROC_BYTES, "entry_guard_stat_size")
    try:
        start, stop = raw.index(b" ("), raw.rindex(b") ")
        pid = int(raw[:start])
        fields = raw[stop + 2:].split()
        _need(len(fields) >= 22, "entry_guard_stat_fields")
        result = {"pid": pid, "ppid": int(fields[1]), "threads": int(fields[17]),
                  "starttime": int(fields[19])}
        for key, value in result.items():
            _integer(value, "entry_guard_stat_" + key, 1 if key != "starttime" else 0)
        return result
    except (ValueError, IndexError) as exc:
        if isinstance(exc, TaskGuardError):
            raise
        raise TaskGuardError("entry_guard_stat_invalid") from exc


def _fdinfo(raw):
    fields = {}
    for line in _text_bytes(raw, "entry_guard_fdinfo", 4096).decode("ascii").splitlines():
        _need(":" in line, "entry_guard_fdinfo_line")
        name, value = line.split(":", 1)
        _need(name not in fields, "entry_guard_fdinfo_duplicate")
        fields[name] = value.strip()
    _need("flags" in fields and re.fullmatch(r"[0-7]+", fields["flags"])
          and "ino" in fields and re.fullmatch(r"[0-9]+", fields["ino"]),
          "entry_guard_fdinfo_fields")
    return int(fields["flags"], 8), int(fields["ino"])


def validate_descriptors(records, expected_fds, launcher_fd=None, receipt_fd=None):
    """Validate the exact observed FD roster; no inferred io_uring absence."""
    _need(type(records) is list and 3 <= len(records) <= MAX_FDS,
          "entry_guard_descriptor_count")
    _same([row.get("fd") if type(row) is dict else None for row in records],
          sorted(expected_fds), "entry_guard_descriptor_roster")
    result = {}
    for row in records:
        _keys(row, ("fd", "link", "fdinfo", "stat", "seals"),
              "entry_guard_descriptor_shape")
        fd = _integer(row["fd"], "entry_guard_descriptor_number", 0, (1 << 20) - 1)
        _text_bytes(row["link"], "entry_guard_descriptor_link", 4096)
        _need("io_uring" not in row["link"], "entry_guard_inherited_io_uring")
        _keys(row["stat"], ("dev", "ino", "mode", "rdev", "size"),
              "entry_guard_descriptor_stat")
        for value in row["stat"].values():
            _integer(value, "entry_guard_descriptor_stat_integer")
        flags, ino = _fdinfo(row["fdinfo"])
        info = row["stat"]
        _need(ino == info["ino"], "entry_guard_descriptor_inode")
        if fd == 0:
            _need(stat.S_ISCHR(info["mode"]) and info["rdev"] == os.makedev(1, 3)
                  and flags & os.O_ACCMODE == os.O_RDONLY and row["link"] == "/dev/null",
                  "entry_guard_stdin")
        elif fd in (1, 2) or fd == receipt_fd:
            _need(stat.S_ISFIFO(info["mode"]) and flags & os.O_ACCMODE == os.O_WRONLY
                  and row["link"] == "pipe:[" + str(ino) + "]",
                  "entry_guard_pipe_descriptor")
        elif fd == launcher_fd:
            _need(stat.S_ISREG(info["mode"]) and row["seals"] == FULL_SEALS
                  and type(row["seals"]) is int and flags & os.O_CLOEXEC,
                  "entry_guard_launcher_descriptor")
        else:
            raise TaskGuardError("entry_guard_unselected_descriptor")
        if fd != launcher_fd:
            _need(row["seals"] is None, "entry_guard_descriptor_unexpected_seals")
        _need(bool(flags & os.O_CLOEXEC) == (fd > 2), "entry_guard_descriptor_cloexec")
        result[fd] = {"fd": fd, "link": row["link"], "stat": info,
                      "flags": flags, "seals": row["seals"]}
    pipes = [(row["stat"]["dev"], row["stat"]["ino"])
             for fd, row in result.items() if fd in (1, 2) or fd == receipt_fd]
    _need(len(pipes) == len(set(pipes)), "entry_guard_pipe_roles_overlap")
    return result


def _status_identity(value, pid, parent_pid):
    _need(value["Pid"] == value["Tgid"] == pid and value["PPid"] == parent_pid
          and value["Threads"] == 1, "entry_guard_process_identity")


def validate_installation(transcript_bytes, program_bytes, *, expected_pid,
                          expected_parent_pid, expected_starttime,
                          expected_launcher_fd, expected_receipt_fd,
                          expected_attempt_id, expected_request_sha256,
                          setup_status_bytes, setup_fd_records,
                          checkpoint_status_bytes=()):
    _need(type(program_bytes) is bytes and program_bytes == PROGRAM_BYTES,
          "entry_guard_program_mismatch")
    record = strict(transcript_bytes)
    _keys(record, ("record_type", "profile", "attempt_id", "request_sha256",
                  "parent_pid", "child_pid", "starttime", "launcher_fd", "receipt_fd",
                  "program", "program_instruction_count", "calls", "proc_stat",
                  "status_before", "status_after", "fd_roster", "physical_authentication",
                  "privileged_filter_readback", "authority_effect"),
          "entry_guard_installation_shape")
    _need(type(expected_attempt_id) is str and re.fullmatch(r"[0-9a-f]{32}", expected_attempt_id)
          and type(expected_request_sha256) is str and _SHA.fullmatch(expected_request_sha256),
          "entry_guard_request_identity")
    for name, expected in (("record_type", INSTALLATION_TYPE), ("profile", PROFILE),
                           ("attempt_id", expected_attempt_id),
                           ("request_sha256", expected_request_sha256),
                           ("parent_pid", expected_parent_pid), ("child_pid", expected_pid),
                           ("starttime", expected_starttime), ("launcher_fd", expected_launcher_fd),
                           ("receipt_fd", expected_receipt_fd), ("program", program_binding()),
                           ("program_instruction_count", PROGRAM_INSTRUCTION_COUNT),
                           ("physical_authentication", False),
                           ("privileged_filter_readback", False), ("authority_effect", "none")):
        _same(record[name], expected, "entry_guard_installation_" + name)
    _integer(expected_pid, "entry_guard_child_pid", 1)
    _integer(expected_parent_pid, "entry_guard_parent_pid", 1)
    _integer(expected_starttime, "entry_guard_starttime")
    _integer(expected_launcher_fd, "entry_guard_launcher_fd", 3, (1 << 20) - 1)
    _integer(expected_receipt_fd, "entry_guard_receipt_fd", 3, (1 << 20) - 1)
    _need(expected_pid != expected_parent_pid and expected_launcher_fd != expected_receipt_fd,
          "entry_guard_owner_roles_overlap")
    _same(record["calls"], [
        {"option": 38, "arg2": 1, "result": 0, "errno": 0},
        {"option": 39, "arg2": 0, "result": 1, "errno": 0},
        {"option": 22, "arg2": 2, "result": 0, "errno": 0},
        {"option": 21, "arg2": 0, "result": 2, "errno": 0},
        {"option": 39, "arg2": 0, "result": 1, "errno": 0},
    ], "entry_guard_installation_calls")
    identity = parse_stat(_text_bytes(record["proc_stat"], "entry_guard_installation_stat"))
    _same(identity, {"pid": expected_pid, "ppid": expected_parent_pid, "threads": 1,
                     "starttime": expected_starttime}, "entry_guard_installation_identity")
    before = parse_status(_text_bytes(record["status_before"], "entry_guard_status_before"))
    after = parse_status(_text_bytes(record["status_after"], "entry_guard_status_after"))
    _status_identity(before, expected_pid, expected_parent_pid)
    _need(before["TracerPid"] == 0 and before["NoNewPrivs"] in (0, 1)
          and ((before["Seccomp"] == 0 and before["Seccomp_filters"] == 0)
               or (before["Seccomp"] == 2 and before["Seccomp_filters"] >= 1)),
          "entry_guard_before_state")
    expected_count = before["Seccomp_filters"] + 1
    _need(after["TracerPid"] == 0, "entry_guard_installer_already_traced")
    for observed in (after, parse_status(setup_status_bytes),
                     *(parse_status(raw) for raw in checkpoint_status_bytes)):
        _status_identity(observed, expected_pid, expected_parent_pid)
        _need(observed["NoNewPrivs"] == 1 and observed["Seccomp"] == 2
              and observed["Seccomp_filters"] == expected_count,
              "entry_guard_enforcement_state_changed")
    installed_fds = validate_descriptors(record["fd_roster"],
        (0, 1, 2, expected_launcher_fd, expected_receipt_fd),
        expected_launcher_fd, expected_receipt_fd)
    setup_fds = validate_descriptors(setup_fd_records, (0, 1, 2, expected_launcher_fd),
                                    expected_launcher_fd)
    del installed_fds[expected_receipt_fd]
    _same(installed_fds, setup_fds, "entry_guard_setup_descriptors_changed")
    return {"program": program_binding(), "child_pid": expected_pid,
            "starttime": expected_starttime, "seccomp_filters": expected_count,
            "installation_transcript_verified": True,
            "evidence_basis": "source_bound_installer_and_procfs",
            "inherited_io_uring_descriptors": 0, **BOUNDARY}


def probe_bytes(name):
    """Pin tiny diagnostic code; it never executes selected original bytes.

    Unexpected syscall return terminates in raw machine code, including vfork,
    so neither an accidental child nor its parent returns into Python frames.
    """
    _need(name in QUALIFICATION_CASES, "entry_guard_qualification_case")
    if name == "compat_getpid":
        code = b"\xb8\x14\x00\x00\x00\xcd\x80"
    else:
        number = (39 if name == "native_getpid" else 39 | X32_SYSCALL_BIT
                  if name == "x32_getpid" else 56 if name == "exec_survival_clone"
                  else BLOCKED_SYSCALLS[name])
        # clone with CLONE_THREAD but without CLONE_SIGHAND is invalid even if
        # a broken filter unexpectedly allows the syscall.
        arg0 = 0x10000 if name in ("clone", "exec_survival_clone") else 0
        code = (b"\xb8" + struct.pack("<I", number) + b"\xbf" + struct.pack("<I", arg0)
                + b"\x31\xf6\x31\xd2\x45\x31\xd2\x45\x31\xc0\x45\x31\xc9\x0f\x05")
    # Only getpid may return successfully. All other unexpected returns exit125.
    exit_code = 0 if name == "native_getpid" else 125
    if name == "native_getpid":
        # A nonpositive syscall result is not an allowed-operation success.
        code += b"\x48\x85\xc0\x7f\x0c\xb8\x3c\x00\x00\x00\xbf\x7d\x00\x00\x00\x0f\x05"
    return code + b"\xb8\x3c\x00\x00\x00\xbf" + struct.pack("<I", exit_code) + b"\x0f\x05\x0f\x0b"


def exec_probe_bytes():
    code = probe_bytes("exec_survival_clone")
    size, entry = 120 + len(code), 0x400000 + 120
    ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    header = struct.pack("<16sHHIQQQIHHHHHH", ident, 2, 62, 1, entry,
                         64, 0, 0, 64, 56, 1, 0, 0, 0)
    segment = struct.pack("<IIQQQQQQ", 1, 5, 0, 0x400000, 0x400000,
                          size, size, 4096)
    return header + segment + code


def validate_environment(value):
    _keys(value, ("uname", "boot_id", "observer", "namespaces"), "entry_guard_environment_shape")
    _keys(value["uname"], ("sysname", "release", "version", "machine"), "entry_guard_uname_shape")
    for item in value["uname"].values():
        _text_bytes(item, "entry_guard_uname_value", 256)
    _need(value["uname"]["sysname"] == "Linux" and value["uname"]["machine"] == "x86_64",
          "entry_guard_environment_platform")
    _need(type(value["boot_id"]) is str and re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", value["boot_id"]),
        "entry_guard_boot_identity")
    _keys(value["observer"], ("size_bytes", "sha256"), "entry_guard_observer_binding")
    _integer(value["observer"]["size_bytes"], "entry_guard_observer_size", 1, 64 * 1024 * 1024)
    _need(type(value["observer"]["sha256"]) is str and _SHA.fullmatch(value["observer"]["sha256"]),
          "entry_guard_observer_digest")
    _keys(value["namespaces"], NAMESPACE_NAMES, "entry_guard_namespaces")
    _need((value["namespaces"]["time"] is None)
          == (value["namespaces"]["time_for_children"] is None),
          "entry_guard_time_namespace_pair")
    for name, link in value["namespaces"].items():
        # These optional kernel interfaces are absent on some diagnostic
        # environments. Their explicit absence is part of the exact context,
        # never an invented namespace identity or hosted qualification.
        if name in ("time", "time_for_children") and link is None:
            continue
        prefix = name.removesuffix("_for_children")
        _need(type(link) is str and re.fullmatch(re.escape(prefix) + r":\[[1-9][0-9]*\]", link),
              "entry_guard_namespace_identity")
    return value


def validate_qualification(raw, *, expected_sources, expected_environment):
    value = strict(raw, MAX_QUALIFICATION_BYTES)
    _keys(value, ("record_type", "profile", "status", "failure", "program", "sources",
                  "environment", "limits", "timing", "cases", *BOUNDARY), "entry_guard_qualification_shape")
    for key, expected in (("record_type", QUALIFICATION_TYPE), ("profile", PROFILE),
                           ("status", "complete"), ("failure", None),
                           ("program", program_binding()), ("sources", expected_sources),
                           ("environment", expected_environment), ("limits", QUALIFICATION_LIMITS),
                           *BOUNDARY.items()):
        _same(value[key], expected, "entry_guard_qualification_" + key)
    _need(type(expected_sources) is list and len(expected_sources) == len(SOURCE_PATHS),
          "entry_guard_qualification_source_roster")
    for item, path in zip(expected_sources, SOURCE_PATHS):
        _keys(item, ("path", "size_bytes", "sha256"), "entry_guard_qualification_source_shape")
        _same(item["path"], path, "entry_guard_qualification_source_path")
        _integer(item["size_bytes"], "entry_guard_qualification_source_size", 1, 1024 * 1024)
        _need(type(item["sha256"]) is str and _SHA.fullmatch(item["sha256"]),
              "entry_guard_qualification_source_digest")
    validate_environment(expected_environment)
    _keys(value["timing"], ("started_ns", "finished_ns"), "entry_guard_qualification_timing")
    started = _integer(value["timing"]["started_ns"], "entry_guard_qualification_started", 1)
    finished = _integer(value["timing"]["finished_ns"], "entry_guard_qualification_finished", started)
    _need(finished - started <= QUALIFICATION_LIMITS["wall_seconds"] * 10**9,
          "entry_guard_qualification_wall_limit")
    _need(type(value["cases"]) is list and len(value["cases"]) == len(QUALIFICATION_CASES),
          "entry_guard_qualification_case_count")
    identities, parents, attempts = set(), set(), set()
    previous_finished = started
    for row, name in zip(value["cases"], QUALIFICATION_CASES):
        _keys(row, ("name", "child_pid", "parent_pid", "starttime", "launcher_fd", "receipt_fd",
                    "attempt_id", "request_sha256", "installation", "setup_status", "setup_fds",
                    "setup_wait_status", "terminal_wait_status", "child_reaped", "cleanup_signal_sent",
                    "resumes", "stdout_hex", "stderr_hex", "probe", "timing"),
              "entry_guard_qualification_case_shape")
        _same(row["name"], name, "entry_guard_qualification_case_order")
        _same(row["probe"], binding(exec_probe_bytes() if name == "exec_survival_clone"
                                    else probe_bytes(name)), "entry_guard_qualification_probe")
        _same(row["request_sha256"], binding(("entry-task-guard:" + name).encode("ascii"))["sha256"],
              "entry_guard_qualification_request")
        validate_installation(_text_bytes(row["installation"], "entry_guard_qualification_installation",
                                         MAX_INSTALLATION_BYTES), PROGRAM_BYTES,
            expected_pid=row["child_pid"], expected_parent_pid=row["parent_pid"],
            expected_starttime=row["starttime"], expected_launcher_fd=row["launcher_fd"],
            expected_receipt_fd=row["receipt_fd"], expected_attempt_id=row["attempt_id"],
            expected_request_sha256=row["request_sha256"],
            setup_status_bytes=_text_bytes(row["setup_status"], "entry_guard_qualification_status"),
            setup_fd_records=row["setup_fds"])
        identity = row["child_pid"], row["starttime"]
        _need(identity not in identities, "entry_guard_qualification_reused_child")
        identities.add(identity)
        parents.add(row["parent_pid"])
        _need(row["attempt_id"] not in attempts, "entry_guard_qualification_reused_attempt")
        attempts.add(row["attempt_id"])
        _same(row["setup_wait_status"], (signal.SIGSTOP << 8) | 127,
              "entry_guard_qualification_setup_stop")
        _same(row["resumes"], 1, "entry_guard_qualification_resumes")
        _same(row["child_reaped"], True, "entry_guard_qualification_unreaped")
        _same(row["cleanup_signal_sent"], False, "entry_guard_qualification_cleanup_used")
        _same(row["stdout_hex"], "", "entry_guard_qualification_stdout")
        _same(row["stderr_hex"], "", "entry_guard_qualification_stderr")
        _keys(row["timing"], ("started_ns", "setup_ns", "resumed_ns", "finished_ns"),
              "entry_guard_qualification_case_timing")
        previous = previous_finished
        for key in ("started_ns", "setup_ns", "resumed_ns", "finished_ns"):
            previous = _integer(row["timing"][key], "entry_guard_qualification_case_" + key,
                                previous, finished)
        _need(row["timing"]["finished_ns"] - row["timing"]["started_ns"]
              <= QUALIFICATION_LIMITS["case_seconds"] * 10**9,
              "entry_guard_qualification_case_limit")
        previous_finished = row["timing"]["finished_ns"]
        terminal = _integer(row["terminal_wait_status"], "entry_guard_qualification_wait", 0, 65535)
        _need((os.WIFEXITED(terminal) and os.WEXITSTATUS(terminal) == 0)
              if name == "native_getpid" else
              (os.WIFSIGNALED(terminal) and os.WTERMSIG(terminal) == signal.SIGSYS),
              "entry_guard_qualification_denial_not_observed")
    _need(len(parents) == 1, "entry_guard_qualification_observer_changed")
    return {"record_type": "required_gate_idempotence_entry_task_guard_qualification_check_v0",
            "profile": PROFILE, "status": "accepted", "program": program_binding(),
            "qualification": binding(raw), "denial_cases": 10, "allowed_cases": 1,
            "evidence_basis": "source_bound_installer_and_owned_benign_probes", **BOUNDARY}
