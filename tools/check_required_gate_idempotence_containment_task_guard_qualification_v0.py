#!/usr/bin/env python3
"""Reconstruct the fixed authored task-guard probe transcript without execution.

The source-bound native producer is never imported. Raw syscall/stop bytes and
owned-removal records establish only the selected guard-probe observations under
the declared observer/kernel trust. They do not authenticate execution, a build,
the startup helper, a complete host qualification or original containment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
RECORD_TYPE = "required_gate_idempotence_containment_task_guard_qualification_v0"
PROFILE = "linux_x86_64_containment_task_guard_probe_qualification_v0"
REPORT_TYPE = RECORD_TYPE.replace("qualification_v0", "qualification_verification_v0")
SCHEMA_PATH = "schemas/required_gate_idempotence_containment_task_guard_qualification_v0.schema.json"
PROBE_PATH = "tools/required_gate_idempotence_containment_task_probe_v0.c"
PRODUCER_PATH = "tools/qualify_required_gate_idempotence_containment_task_guard_v0.py"
CHECKER_PATH = "tools/check_required_gate_idempotence_containment_task_guard_qualification_v0.py"
FROZEN_SOURCES = {
    "tools/check_required_gate_idempotence_containment_task_guard_v0.py": (40713, "5be04d1fbf22c9de4ae0a93d9348ef0740568b68be9c3d60c6027dedb04085ad"),
    "tools/required_gate_idempotence_containment_task_guard_v0.py": (19568, "b073d370c8081337cb658929a53802bdbfa73d4f0bf4bf677dc716ef9dd76802"),
    "tools/required_gate_idempotence_containment_startup_v0.c": (27461, "0ae15697c524fc13c2ac0f04d2a1c1d44c7e5952e6b285a4add2799a740d4409"),
    "docs/compute/required_gate_idempotence_containment_task_guard_v0/contract_v0.json": (12962, "20a17df1c1307ef5113044335ee70b8aa96d7d68322f1acc1fe5e9a18ba8bf64"),
    "schemas/required_gate_idempotence_containment_task_guard_v0.schema.json": (116458, "97b753934024c4253a217ab9e906824d016d6144a27f615f7ed678dc5abada44"),
    "docs/compute/required_gate_idempotence_containment_entry_plan_v0/plan_v0.json": (21284, "dee57c7b8e4abf86227404ba4c9efc51ced69633e1128295a2d2cef8b78318e0"),
    "docs/compute/required_gate_idempotence_containment_entry_plan_v0/source_bindings_v0.json": (21350, "80190d88ac4e0b654cd8a315b67062aab171a24f81d9fa99108c6d7351930fd0"),
}
SOURCE_PATHS = tuple(sorted((CHECKER_PATH, PRODUCER_PATH, PROBE_PATH, SCHEMA_PATH, *FROZEN_SOURCES)))
CASES = ("native_getpid", "fork", "vfork", "clone3", "io_uring_setup", "io_uring_enter",
         "io_uring_register", "x32_getpid", "compat_getpid", "clone_unselected",
         "clone_l_upper", "clone_l_stack", "clone_r_null_tid", "clone_r_parent_tid",
         "clone_r_tls", "clone_r_stack", "clone_r_upper", "clone_r_unselected",
         "exec_denial", "graph_inheritance", "graph_cancel")
LIMITS = {"observation_seconds": 120, "case_seconds": 5, "cleanup_seconds": 5,
          "cases": 21, "tasks_per_case": 3, "events_per_case": 8192,
          "events_total": 65536, "record_bytes": 33554432, "probe_bytes": 262144,
          "raw_read_bytes": 65536, "memory_bytes_per_stop": 1048576,
          "stdout_bytes": 4096, "stderr_bytes": 4096, "attempts": 1, "retries": 0}
BOUNDARY = {"diagnostic_only": True, "startup_helper_execution_observed": False,
            "executed_helper_build_admitted": False, "full_host_qualification_completed": False,
            "original_native_acquisition_performed": False, "containment_observed": False,
            "source_binary_equivalence_verified": False, "physical_execution_authenticated": False,
            "privileged_filter_readback": False, "execution_authorized": False,
            "b2_complete": False, "metric_pass": None, "authority_effect": "none"}
GUARD_BYTES = bytes.fromhex(
    "20000000040000001500001f3e0000c0200000000000000045001d0000000040"
    "15001c003900000015001b003a00000015001a00a901000015001900aa010000"
    "15001800ab01000015001700b301000015000015380000002000000014000000"
    "150000140000000020000000180000001500001200000000200000001c000000"
    "1500001000000000200000001000000015000d001100027e1500000d11002001"
    "20000000200000001500000b0000000020000000240000001500000900000000"
    "2000000030000000150000070000000020000000340000001500000500000000"
    "20000000280000001500000200000000200000002c0000001500010000000000"
    "060000000000ff7f0600000000000080")
PTRACE_OPTIONS = 0x0010001F
MARKER = 0x50554C5345515630
ARCH = 0xC000003E
U64 = (1 << 64) - 1
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_CODE = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")


class QualificationError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def need(condition, code):
    if not condition:
        raise QualificationError("containment_guard_qualification_" + code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                       allow_nan=False) + "\n").encode("ascii")


def binding(raw):
    need(type(raw) is bytes, "binding_type")
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def integer(value, code="integer", low=0, high=U64):
    need(type(value) is int and low <= value <= high, code)
    return value


def keys(value, names, code):
    need(type(value) is dict and set(value) == set(names), code)


def same(actual, expected, code):
    need(canonical(actual) == canonical(expected), code)


def digest(value, code="digest"):
    need(type(value) is str and _SHA.fullmatch(value) is not None, code)
    return value


def unhex(value, maximum=65536, *, size=None, empty=False):
    need(type(value) is str and len(value) <= maximum * 2 and len(value) % 2 == 0
         and (bool(value) or empty) and re.fullmatch(r"[0-9a-f]*", value), "raw_hex")
    raw = bytes.fromhex(value)
    need(size is None or len(raw) == size, "raw_size")
    return raw


def _pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, "duplicate_key")
        result[key] = value
    return result


def _number(_value):
    raise QualificationError("containment_guard_qualification_noninteger_json")


def parse(raw, maximum=33554432):
    need(type(raw) is bytes and 0 < len(raw) <= maximum, "record_extent")
    try:
        value = json.loads(raw.decode("ascii"), object_pairs_hook=_pairs,
                           parse_float=_number, parse_constant=_number)
    except QualificationError:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise QualificationError("containment_guard_qualification_invalid_json") from exc
    stack, count = [(value, 0)], 0
    while stack:
        item, depth = stack.pop()
        count += 1
        need(depth <= 20 and count <= 2000000, "json_structure")
        if type(item) is dict:
            need(all(type(key) is str and 0 < len(key) <= 128 for key in item), "json_key")
            stack.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            need(len(item) <= 65536, "json_list")
            stack.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            need(len(item) <= 524288, "json_string")
        else:
            need(item is None or type(item) is bool or
                 type(item) is int and -U64 <= item <= U64, "json_scalar")
    need(raw == canonical(value), "noncanonical_json")
    return value


def _read(path, maximum):
    # Directory components are opened without following aliases.
    path = Path(path).absolute()
    opened = []
    try:
        fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        opened.append(fd)
        for part in path.parts[1:-1]:
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
            opened.append(fd)
        leaf = os.open(path.name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        opened.append(leaf)
        before = os.fstat(leaf)
        need((before.st_mode & 0o170000) == 0o100000 and before.st_nlink == 1
             and 0 < before.st_size <= maximum, "input_file")
        raw = bytearray()
        while len(raw) <= maximum:
            block = os.read(leaf, min(65536, maximum + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
        after = os.fstat(leaf)
        need(len(raw) == before.st_size and len(raw) <= maximum and
             (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
             (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), "input_changed")
        return bytes(raw)
    finally:
        for fd in reversed(opened):
            os.close(fd)


def source_bytes(root=ROOT):
    result = {path: _read(Path(root) / path, 1048576) for path in SOURCE_PATHS}
    for path, (size, sha) in FROZEN_SOURCES.items():
        need(binding(result[path]) == {"size_bytes": size, "sha256": sha}, "frozen_source_changed")
    return result


def verify_prerequisite_source_contract():
    """Freshly reconstruct frozen source policy from its preserved originals."""
    path = "tools/check_required_gate_idempotence_containment_task_guard_v0.py"
    selected_size, selected_sha = FROZEN_SOURCES[path]
    need(binding(_read(ROOT / path,1048576)) == {"size_bytes":selected_size,"sha256":selected_sha},
         "prerequisite_checker_changed")
    sys.path.insert(0,str(ROOT / "tools"))
    import check_required_gate_idempotence_containment_task_guard_v0 as prior
    try:
        raw = _read(ROOT / prior.CONTRACT_REL,1048576)
        result = prior.verify_contract(contract_bytes=raw,
            expected_contract_sha256=FROZEN_SOURCES[prior.CONTRACT_REL][1],
            inputs=prior.load_inputs(ROOT))
        need(result["record_status"] == "verified_source_contract"
             and result["task_guard_program"]["sha256"] == binding(GUARD_BYTES)["sha256"],
             "prerequisite_contract")
        return result
    except prior.ContractError as exc:
        raise QualificationError("containment_guard_qualification_prerequisite_contract") from exc


def source_inventory(root=ROOT, inputs=None):
    selected = source_bytes(root) if inputs is None else dict(inputs)
    keys(selected, SOURCE_PATHS, "source_roster")
    for path, (size, sha) in FROZEN_SOURCES.items():
        need(binding(selected[path]) == {"size_bytes": size, "sha256": sha}, "frozen_source_changed")
    return [{"path": path, **binding(selected[path])} for path in SOURCE_PATHS]


def parse_stat(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 65536 and b"\0" not in raw, "stat_bytes")
    try:
        stop = raw.rindex(b") ")
        head = raw[:stop].split(b" (", 1)
        fields = raw[stop + 2:].split()
        need(len(head) == 2 and len(fields) >= 22, "stat_fields")
        return {"pid": integer(int(head[0]), "stat_pid", 1, 2147483647),
                "state": fields[0].decode("ascii"), "ppid": int(fields[1]),
                "threads": int(fields[17]), "starttime": int(fields[19])}
    except (ValueError, UnicodeError, IndexError) as exc:
        if isinstance(exc, QualificationError):
            raise
        raise QualificationError("containment_guard_qualification_stat_invalid") from exc


def parse_status(raw):
    try:
        fields = {}
        for line in raw.decode("ascii").splitlines():
            name, val = line.split(":", 1)
            need(name not in fields, "status_duplicate")
            fields[name] = val.strip()
        for name in ("Pid", "Tgid", "PPid", "TracerPid", "Threads", "NoNewPrivs", "Seccomp", "Seccomp_filters"):
            need(name in fields and re.fullmatch(r"[0-9]+", fields[name]), "status_fields")
        return fields
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, QualificationError):
            raise
        raise QualificationError("containment_guard_qualification_status_invalid") from exc


def _initial_credentials(status):
    for name in ("Uid", "Gid"):
        values = status.get(name, "").split()
        need(len(values) == 4 and all(re.fullmatch(r"[0-9]+", value) for value in values), "initial_credentials")
        need(int(values[0]) > 0 and values[0] == values[1], "initial_nonroot_equal_ids")
    for name in ("CapEff", "CapPrm", "CapInh"):
        value = status.get(name, "")
        need(re.fullmatch(r"[0-9a-fA-F]{16}", value) and int(value, 16) == 0, "initial_capabilities")


def syscall_info(raw):
    need(len(raw) in (24, 33, 80, 84), "syscall_info_extent")
    op, arch, ip, sp = struct.unpack_from("<B3xIQQ", raw)
    need(raw[1:4] == b"\0\0\0", "syscall_info_padding")
    result = {"op": op, "arch": arch, "ip": ip, "sp": sp}
    if op == 1:
        need(len(raw) == 80, "syscall_entry_extent")
        values = struct.unpack_from("<7Q", raw, 24)
        result.update(number=values[0], args=values[1:])
    elif op == 2:
        need(len(raw) == 33 and raw[32] in (0, 1), "syscall_exit_extent")
        result.update(result=struct.unpack_from("<q", raw, 24)[0], error=raw[32])
    else:
        need(op == 0 and len(raw) == 24, "syscall_info_op")
    return result


def _writable(raw, address, extent=4):
    integer(address, "memory_address", 1, U64 - extent)
    try:
        for line in raw.decode("ascii").splitlines():
            fields = line.split()
            need(len(fields) >= 5, "maps_line")
            bounds = fields[0].split("-")
            need(len(bounds) == 2 and re.fullmatch(r"[0-9a-f]+", bounds[0])
                 and re.fullmatch(r"[0-9a-f]+", bounds[1]), "maps_bounds")
            low, high = map(lambda item: int(item, 16), bounds)
            if low <= address and address + extent <= high:
                return len(fields[1]) == 4 and fields[1][1] == "w"
    except (UnicodeError, ValueError):
        return False
    return False


def _readonly_mapping(raw, address, extent):
    need(type(raw) is bytes and 0 < len(raw) <= 65536,"guard_maps_extent")
    matches = []
    try:
        for line in raw.decode("ascii").splitlines():
            fields = line.split()
            need(len(fields) >= 5,"guard_maps_line")
            low, high = (int(item,16) for item in fields[0].split("-"))
            if low <= address and address + extent <= high:
                need(len(fields[1]) == 4 and fields[1][0] == "r"
                     and fields[1][1] == "-" and fields[1][3] == "p",
                     "guard_mapping_writable_or_shared")
                matches.append(line)
    except (UnicodeError,ValueError) as exc:
        if isinstance(exc,QualificationError):
            raise
        raise QualificationError("containment_guard_qualification_guard_maps_invalid") from exc
    need(len(matches) == 1,"guard_mapping_roster")
    return matches[0]


def _memory(event, address, extent):
    found = [unhex(row["hex"], 65536) for row in event["memory"] if row["address"] == address]
    need(len(found) == 1 and len(found[0]) == extent, "memory_missing_or_extent")
    return found[0]


def _negative(case_id, number, args, arch):
    zero = (0,) * 6
    simple = {2:57, 3:58, 4:435, 5:425, 6:426, 7:427, 8:0x40000027}
    if case_id in simple:
        return arch == ARCH and number == simple[case_id] and args == zero
    if case_id == 9:
        return arch == 0x40000003 and number == 20 and args == zero
    if arch != ARCH or number != 56:
        return False
    if case_id == 10:
        return args == (17, 0, 0, 0, 0, 0)
    if case_id == 11:
        return args == (0x17e020011, 0, 0xa2, 0xa3, 0xa4, 0xa5)
    if case_id == 12:
        return args == (0x7e020011, 0x100000000, 0xa2, 0xa3, 0xa4, 0xa5)
    if 13 <= case_id <= 18:
        expected = [0x01200011, 0, 0, args[3], 0, 0xa5]
        if case_id == 13:
            expected[3] = 0
        else:
            if args[3] == 0:
                return False
        if case_id == 14: expected[2] = 0x100000000
        if case_id == 15: expected[4] = 0x100000000
        if case_id == 16: expected[1] = 0x100000000
        if case_id == 17: expected[0] = 0x101200011
        if case_id == 18: expected[0] = 0x01200111
        return args == tuple(expected)
    return False


def validate_event_structure(event):
    need(type(event) is dict,"event_shape")
    integer(event.get("seq"),"event_sequence",0,8191)
    integer(event.get("t_ns"),"event_time")
    op = event.get("op")
    shapes = {
        "spawn": ("pid","pidfd","raw"), "acquire": ("pid","pidfd","raw"),
        "seize": ("pid","options"), "interrupt": ("pid",), "release": ("pid",),
        "wait": ("pid","status","raw","memory"), "resume": ("pid","request","signal"),
        "cleanup_begin": ("reason",), "pidfd_signal": ("pid","pidfd","signal","result","errno"),
        "pidfd_poll": ("pid","pidfd","revents"), "wait_drained": ("errno",),
        "failure": ("code","errno")}
    need(op in shapes, "event_operation")
    keys(event, ("seq","t_ns","op",*shapes[op]), "event_shape")
    if "pid" in event:
        integer(event["pid"],"event_pid",2,2147483647)
    if "pidfd" in event:
        integer(event["pidfd"],"event_pidfd",3,(1<<20)-1)
    if "errno" in event:
        integer(event["errno"],"event_errno",0,4095)
    if op in ("spawn","acquire"):
        keys(event["raw"],("stat","status","pidfd_info"),"owned_raw")
        for raw in event["raw"].values():
            unhex(raw)
    elif op == "seize":
        need(type(event["options"]) is int and event["options"] == PTRACE_OPTIONS,"seize_options")
    elif op == "resume":
        need(event["request"] in ("cont","syscall") and type(event["signal"]) is int
             and event["signal"] in (0,17),"resume_shape")
    elif op == "cleanup_begin":
        need(event["reason"] in ("normal","failure"),"cleanup_reason")
    elif op == "pidfd_signal":
        need(type(event["signal"]) is int and event["signal"] == 9
             and type(event["result"]) is int and event["result"] in (-1,0),"signal_shape")
    elif op == "pidfd_poll":
        integer(event["revents"],"poll_revents",0,65535)
    elif op == "wait_drained":
        need(event["errno"] == 10,"wait_drained_errno")
    elif op == "failure":
        need(type(event["code"]) is str and _CODE.fullmatch(event["code"]),"failure_code")
    if op == "wait":
        integer(event["status"],"wait_status",0,(1<<32)-1)
        need(type(event["raw"]) is dict and set(event["raw"]) <= {
            "regs","syscall_info","event_message","stat","status","maps","exe","cmdline","environ","siginfo"}, "wait_raw_roster")
        for name, raw in event["raw"].items():
            unhex(raw, 262144 if name == "exe" else 65536)
        need(type(event["memory"]) is list and len(event["memory"]) <= 16, "memory_roster")
        addresses, total = set(), 0
        for item in event["memory"]:
            keys(item, ("address","hex"), "memory_shape")
            address = integer(item["address"], "memory_address", 1)
            need(address not in addresses, "memory_duplicate")
            addresses.add(address)
            total += len(unhex(item["hex"]))
        need(total <= 1048576, "memory_budget")


class TraceState:
    """Pure per-case replay; the live controller asks before every restart.

    Newborn waits and parent birth messages can arrive in either order. Pending
    children have no resume permission until their identity join is complete.
    A task identity may have multiple terminal waits before final real-parent
    removal; terminal status alone does not finish cleanup.
    """
    def __init__(self, case_id, observer_pid, probe_bytes):
        self.case_id = integer(case_id, "case_id", 1, 21)
        self.observer_pid = integer(observer_pid, "observer_pid", 2, 2147483647)
        need(type(probe_bytes) is bytes and 0 < len(probe_bytes) <= LIMITS["probe_bytes"], "probe_extent")
        self.probe_bytes = probe_bytes
        self.guard_address = verify_probe_elf(probe_bytes,
            expected_probe_sha256=binding(probe_bytes)["sha256"])["guard_address"]
        self.tasks, self.roles, self.pending = {}, {}, {}
        self.seq, self.time = 0, 0
        self.cleanup, self.failure, self.drained = False, False, False
        self.signals = []
        self.releases = 0
        self.births = 0
        self.terminal_ready = False
        self.finished = False

    def _task(self, pid):
        integer(pid, "event_pid", 2, 2147483647)
        need(pid in self.tasks, "unowned_task")
        return self.tasks[pid]

    def _identity(self, pid, raw, *, stopped=False, traced=False):
        stat = parse_stat(unhex(raw["stat"]))
        status = parse_status(unhex(raw["status"]))
        need(stat["pid"] == pid and stat["threads"] == 1 and stat["starttime"] > 0
             and int(status["Pid"]) == pid and int(status["Tgid"]) == pid
             and int(status["Threads"]) == 1 and int(status["PPid"]) == stat["ppid"], "task_identity")
        if pid == self.roles.get(0):
            _initial_credentials(status)
        if stopped:
            need(stat["state"] == "t", "task_not_stopped")
        if traced:
            need(int(status["TracerPid"]) == self.observer_pid, "task_tracer")
        task = self.tasks.get(pid)
        if task is not None:
            need(task["starttime"] == stat["starttime"], "task_reused")
            if task["parent"] is not None and not self.cleanup:
                need(stat["ppid"] == task["parent"], "task_parent")
        return stat, status

    def _own(self, event, role=None):
        pid, pidfd = event["pid"], event["pidfd"]
        integer(pid, "owned_pid", 2, 2147483647)
        integer(pidfd, "owned_pidfd", 3, (1 << 20) - 1)
        need(pid != self.observer_pid and pid not in self.tasks and len(self.tasks) < 3
             and all(t["pidfd"] != pidfd for t in self.tasks.values()), "owned_identity")
        keys(event["raw"], ("stat", "status", "pidfd_info"), "owned_raw")
        stat, status = self._identity(pid, event["raw"])
        if role == 0:
            _initial_credentials(status)
        info = unhex(event["raw"]["pidfd_info"]).decode("ascii")
        fields = {}
        for line in info.splitlines():
            name, value = line.split(":", 1)
            need(name not in fields, "pidfd_info_duplicate")
            fields[name] = value.strip()
        need(fields.get("Pid") == str(pid) and re.fullmatch(r"[0-7]+", fields.get("flags", ""))
             and int(fields["flags"], 8) & os.O_CLOEXEC, "pidfd_identity")
        self.tasks[pid] = {"pid": pid, "pidfd": pidfd, "role": role, "parent": self.observer_pid if role == 0 else None,
            "starttime": stat["starttime"], "stopped": False, "seized": False, "interrupted": False,
            "interrupt_consumed": False, "execs": 0, "stage": 0, "entry": None,
            "filter_before": None, "filter_count": None, "guard": False, "install": None,
            "clone_child": None, "clone_result": None, "ctid": None, "negative": False,
            "park": False, "terminal": [], "hup": False, "reaped_marker": False,
            "control": False, "last_status": status, "newborn_stopped": False,
            "exec_exit_pending": False, "newborn_return": False, "pending_signal": 0, "sigchld_seen": False,
            "nnp_set": False, "nnp_read_before": False, "nnp_read_after": False, "seccomp_read_after": False,
            "wait4_restart_args": None, "wait4_restart_count": 0, "restart_signal_seen": False,
            "restart_signal_forwarded": False}
        if role is not None:
            need(role not in self.roles and stat["ppid"] == self.observer_pid, "spawn_parent")
            self.roles[role] = pid
        if pid in self.pending:
            wait = self.pending.pop(pid)
            self._wait(wait)

    def can_resume(self, pid, request="syscall"):
        task = self._task(pid)
        need(request in ("cont", "syscall"), "restart_request")
        if self.cleanup or task["terminal"] or task["park"] or task["role"] is None or not task["stopped"]:
            return False
        if task["clone_child"] is not None and not self.tasks[task["clone_child"]]["newborn_stopped"]:
            return False
        if task["pending_signal"] and not self.tasks[task["clone_child"]]["terminal"]:
            return False
        if request == "cont":
            return task["role"] == 0 and task["execs"] == 0 and task["interrupt_consumed"] and self.releases == 1
        return task["execs"] > 0 and (task["role"] == 0 or
                task["parent"] is not None and task["newborn_stopped"])

    def _exec(self, event, task):
        raw = event["raw"]
        need(task["role"] is not None and not task["park"], "exec_role")
        phase = "initial" if task["execs"] == 0 and task["role"] == 0 else "after-exec"
        if phase == "initial":
            need(self.releases == 1 and task["interrupt_consumed"], "initial_exec_before_release")
        else:
            need(task["guard"] and task["entry"] is not None and task["entry"][0] == 322
                 and ((self.case_id == 19 and task["role"] == 0) or
                      (self.case_id in (20, 21) and task["role"] == 2))
                 and task["execs"] <= 1, "unexpected_exec")
        need(unhex(raw["exe"], 262144) == self.probe_bytes, "exec_bytes")
        expected = ["pulsemech-containment-task-probe-v0", CASES[self.case_id-1], str(self.observer_pid), phase]
        need(unhex(raw["cmdline"]) == ("\0".join(expected) + "\0").encode("ascii")
             and unhex(raw["environ"]) == b"LC_ALL=C\0TZ=UTC\0", "exec_vectors")
        regs = struct.unpack("<27Q", unhex(raw["regs"], size=216))
        need(len(self.probe_bytes) >= 64 and regs[16] == struct.unpack_from("<Q", self.probe_bytes, 24)[0]
             and regs[18] & 0x100 == 0, "exec_entry")
        task["execs"] += 1
        task["entry"] = None
        task["exec_exit_pending"] = True
        if phase == "after-exec":
            task["nnp_read_after"] = False
            task["seccomp_read_after"] = False

    def _marker(self, event, task, args, status):
        _, case_id, stage, role, value0, value1 = args
        need(case_id == self.case_id and role == task["role"], "marker_identity")
        if stage == 1:
            need(role == 0 and task["execs"] == 1 and task["stage"] == 0 and value0 == value1 == 0, "preinstall_marker")
            task["filter_before"] = int(status["Seccomp_filters"])
        elif stage == 2:
            need(role == 0 and task["stage"] == 1 and task["guard"] and task["nnp_read_after"]
                 and task["seccomp_read_after"] and value0 == value1 == 0
                 and int(status["NoNewPrivs"]) == 1 and int(status["Seccomp"]) == 2
                 and int(status["Seccomp_filters"]) == task["filter_before"] + 1, "postinstall_marker")
            task["filter_count"] = int(status["Seccomp_filters"])
        elif stage == 3:
            need(self.case_id in (20,21) and role == 1 and task["stage"] == 0 and task["guard"]
                 and value0 == value1 == 0, "r_born_marker")
        elif stage == 4:
            need(self.case_id in (20,21) and role == 2 and task["stage"] == 0 and task["guard"]
                 and value0 == task["ctid"] and value1 > 0, "t_born_marker")
            need(_writable(unhex(event["raw"]["maps"]), value0)
                 and struct.unpack("<I", _memory(event, value0, 4))[0] == value1, "ctid_written")
            nspid = status.get("NSpid", "").split()
            need(nspid and all(re.fullmatch(r"[0-9]+", item) for item in nspid)
                 and int(nspid[-1]) == value1, "ctid_namespace_pid")
        elif stage == 5:
            need(task["guard"] and task["nnp_read_after"] and task["seccomp_read_after"]
                 and value0 == value1 == 0 and
                 ((self.case_id == 19 and role == 0 and task["execs"] == 2 and task["stage"] == 2) or
                  (self.case_id in (20,21) and role == 2 and task["execs"] == 2 and task["stage"] == 4)), "after_exec_marker")
        elif stage == 6:
            need(self.case_id == 21 and value0 == value1 == 0 and
                 ((role == 0 and task["stage"] == 2 and task["clone_result"] is not None) or
                  (role == 1 and task["stage"] == 3 and task["clone_result"] is not None) or
                  (role == 2 and task["stage"] == 5)), "park_marker")
            task["park"] = True
        elif stage == 7:
            need(self.case_id == 20 and role in (0,1) and not task["reaped_marker"]
                 and task["clone_result"] == value0 and value0 > 0
                 and value1 & ~128 == 31, "reaped_marker")
            child = self.tasks[task["clone_child"]]
            need(child["terminal"] and child["terminal"][-1] & 127 == 31, "reaped_child_missing")
            task["reaped_marker"] = True
        elif stage == 8:
            need(self.case_id == 1 and role == 0 and task["stage"] == 2 and value0 == value1 == 0, "control_marker")
            task["control"] = True
        else:
            need(False, "marker_stage")
        task["stage"] = stage
        if task["guard"]:
            need(int(status["NoNewPrivs"]) == 1 and int(status["Seccomp"]) == 2
                 and int(status["Seccomp_filters"]) == task["filter_count"], "guard_inheritance_state")

    def _entry(self, event, task, info, status):
        number, args, arch = info["number"], info["args"], info["arch"]
        if task["exec_exit_pending"]:
            # Kernel reports may proceed directly to the first entry. Neither
            # path invents a missing successful syscall return observation.
            task["exec_exit_pending"] = False
        if task["newborn_return"]:
            task["entry"] = None
            task["newborn_return"] = False
        need(task["entry"] is None and task["execs"] > 0 and not task["park"], "syscall_entry_order")
        if task["wait4_restart_args"] is not None:
            need(number == 61 and arch == ARCH and args == task["wait4_restart_args"]
                 and task["restart_signal_seen"] and task["restart_signal_forwarded"],
                 "wait4_restart_sequence")
            task["wait4_restart_args"] = None
        if number == 39 and arch == ARCH and args[0] == MARKER:
            self._marker(event, task, args, status)
        elif not task["guard"]:
            need(arch == ARCH and task["role"] == 0 and task["stage"] == 1
                 and number in (5,72,102,104,107,108,110,125,157), "unguarded_syscall")
            if number == 157 and args[0] == 22:
                need(args[1] == 2 and args[2] > 0 and args[3:] == (0,0,0) and task["install"] is None
                     and task["nnp_set"] and task["nnp_read_before"], "guard_submission")
                header = _memory(event, args[2], 16)
                length, pointer = struct.unpack("<H6xQ", header)
                need(length == 34 and pointer == self.guard_address and _memory(event, pointer, 272) == GUARD_BYTES,
                     "guard_program_bytes")
                mapping = _readonly_mapping(unhex(event["raw"]["maps"]),pointer,272)
                task["install"] = (args[2], pointer, header, mapping)
            elif number == 157:
                need(args[0] in (1,2,21,38,39), "preinstall_prctl")
                if args[0] == 1:
                    need(args[1:] == (9,0,0,0,0), "pdeathsig_submission")
                elif args[0] == 2:
                    need(args[1] > 0 and args[2:] == (0,0,0,0), "pdeathsig_readback")
                elif args[0] == 38:
                    need(args[1:] == (1,0,0,0,0), "nnp_submission")
                else:
                    need(args[1:] == (0,0,0,0,0), "prctl_readback_arguments")
        elif _negative(self.case_id, number, args, arch) and task["role"] == 0 and task["stage"] == 2:
            need(not task["negative"], "duplicate_negative")
            task["negative"] = True
        elif number == 57 and arch == ARCH and args == (0,)*6 and self.case_id in (19,20):
            need((self.case_id == 19 and task["role"] == 0 and task["stage"] == 5) or
                 (self.case_id == 20 and ((task["role"] == 2 and task["stage"] == 5) or
                                          (task["role"] in (0,1) and task["reaped_marker"]))), "inheritance_denial_order")
            need(not task["negative"], "duplicate_negative")
            task["negative"] = True
        elif number == 56 and arch == ARCH and self.case_id in (20,21):
            need(task["role"] in (0,1) and task["clone_child"] is None, "clone_role_or_count")
            if task["role"] == 0:
                need(task["stage"] == 2 and self.births == 0 and args == (0x7e020011,0,0xa2,0xa3,0xa4,0xa5), "clone_l_shape")
            else:
                need(task["stage"] == 3 and self.births == 1 and args[0:3] == (0x01200011,0,0)
                     and args[3] > 0 and args[4:] == (0,0xa5), "clone_r_shape")
                need(_writable(unhex(event["raw"]["maps"]), args[3])
                     and _memory(event, args[3], 4) == b"\0"*4, "clone_r_ctid")
                task["ctid"] = args[3]
        elif number == 322 and arch == ARCH:
            need(((self.case_id == 19 and task["role"] == 0 and task["stage"] == 2) or
                  (self.case_id in (20,21) and task["role"] == 2 and task["stage"] == 4))
                 and args[0] == 3 and args[1] > 0 and args[2] > 0 and args[3] > 0
                 and args[4:] == (4096,0), "self_exec_shape")
            need(_memory(event,args[1],1) == b"\0", "self_exec_empty_path")
        elif number == 61 and arch == ARCH:
            need(self.case_id == 20 and task["role"] in (0,1) and task["clone_result"] is not None
                 and args[0] == task["clone_result"] and args[1] > 0 and args[2:] == (0,0,0,0), "wait4_shape")
        elif number == 60 and arch == ARCH:
            need(self.case_id == 1 and task["control"] and args == (0,)*6, "exit_shape")
        else:
            need(arch == ARCH and number in (39,72,110,157), "unexpected_syscall")
            if number == 39:
                need(args == (0,)*6, "getpid_arguments")
            elif number == 72:
                need(args in ((3,2,1,0,0,0),(3,1,0,0,0,0)) and
                     (self.case_id == 19 or task["role"] == 2), "self_exec_descriptor")
            elif number == 110:
                need(task["role"] == 0 and task["stage"] == 1 and args == (0,)*6, "guarded_parent_check")
            elif number == 157:
                need(args[0] in (21,39) and args[1:] == (0,)*5, "guarded_prctl")
        task["entry"] = (number, args, arch)

    def _exit(self, event, task, info):
        if task["exec_exit_pending"]:
            need(task["entry"] is None and info["arch"] == ARCH and info["result"] == 0
                 and info["error"] == 0, "exec_syscall_exit")
            task["exec_exit_pending"] = False
            return
        need(task["entry"] is not None, "syscall_exit_order")
        number, args, arch = task["entry"]
        result = info["result"]
        need(info["arch"] == arch and not task["negative"], "negative_syscall_returned")
        if number == 157 and args[0] == 22:
            need(result == 0 and info["error"] == 0 and task["install"] is not None, "guard_submission_return")
            header_address, program_address, header, mapping = task["install"]
            need(_memory(event, header_address, 16) == header and
                 _memory(event, program_address, 272) == GUARD_BYTES and
                 _readonly_mapping(unhex(event["raw"]["maps"]),program_address,272) == mapping,
                 "guard_submission_changed")
            task["guard"] = True
            task["filter_count"] = task["filter_before"] + 1
        elif number == 56:
            if task["clone_child"] is not None:
                need(result > 0 and info["error"] == 0, "allowed_clone_failed")
                child = self.tasks[task["clone_child"]]
                if task["role"] == 0:
                    need(result == child["pid"],"clone_l_child_result")
                else:
                    pids = child["last_status"].get("NSpid", "").split()
                    need(len(pids) >= 2 and all(re.fullmatch(r"[0-9]+",item) for item in pids)
                         and result == int(pids[-1]),"clone_r_child_result")
                task["clone_result"] = result
            else:
                need(result == 0 and info["error"] == 0 and task["role"] in (1,2), "newborn_clone_return")
        elif number == 61:
            if result == -512 and info["error"] == 1:
                need(self.case_id == 20 and task["role"] in (0,1)
                     and task["wait4_restart_count"] == 0 and not task["sigchld_seen"],
                     "wait4_restart_limit")
                task["wait4_restart_count"] = 1
                task["wait4_restart_args"] = args
            else:
                need(result == task["clone_result"] and info["error"] == 0, "wait4_return")
        elif number == 322:
            need(False, "exec_failed")
        else:
            need(info["error"] == 0 and result >= 0, "probe_syscall_failed")
            if number == 39:
                pids = task["last_status"].get("NSpid",str(task["pid"])).split()
                need(pids and all(re.fullmatch(r"[0-9]+",item) for item in pids)
                     and result == int(pids[-1]), "getpid_result")
            if number == 157:
                expected = 1 if args[0] == 39 else 2 if args[0] == 21 else 0
                need(result == expected, "prctl_result")
                if args[0] == 38:
                    need(not task["nnp_set"],"nnp_duplicate_set")
                    task["nnp_set"] = True
                elif args[0] == 39:
                    if task["guard"]:
                        task["nnp_read_after"] = True
                    else:
                        need(task["nnp_set"],"nnp_read_before_set")
                        task["nnp_read_before"] = True
                elif args[0] == 21 and task["guard"]:
                    task["seccomp_read_after"] = True
        task["entry"] = None
        task["newborn_return"] = False

    def _wait(self, event):
        pid, status = event["pid"], integer(event["status"], "wait_status", 0, (1 << 32)-1)
        if pid not in self.tasks:
            need(not self.cleanup and len(self.pending) < 2 and pid not in self.pending
                 and status in (0x0080057f,0x0080137f), "unknown_wait")
            self.pending[pid] = event
            return
        task = self.tasks[pid]
        if status & 0xff == 0x7f:
            if self.cleanup:
                # SIGKILL can race a previously queued stop. Proc/memory reads
                # may already be unavailable; preserving that consumed status
                # does not authorize a restart or prove final removal.
                need(not task["terminal"], "stop_after_terminal")
                task["stopped"] = True
                return
            need(not task["terminal"] and not task["stopped"], "duplicate_stop")
            stat, fields = self._identity(pid, event["raw"], stopped=True, traced=True)
            task["last_status"] = fields
            task["stopped"] = True
            event_id, sig = status >> 16, (status >> 8) & 0xff
            regs = struct.unpack("<27Q", unhex(event["raw"]["regs"], size=216))
            if self.cleanup:
                return
            if event_id == 128:
                need(sig in (5,19), "event_stop_signal")
                if task["role"] == 0:
                    need(task["seized"] and task["interrupted"] and not task["interrupt_consumed"]
                         and task["execs"] == 0, "interrupt_stop")
                    task["interrupt_consumed"] = True
                else:
                    need(not task["newborn_stopped"], "newborn_stop")
                    task["newborn_stopped"] = True
                return
            if event_id == 4:
                need(sig == 5 and struct.unpack("<Q", unhex(event["raw"]["event_message"], size=8))[0] == pid,
                     "exec_event_message")
                self._exec(event, task)
                return
            if event_id == 1:
                need(sig == 5 and task["entry"] is not None and task["entry"][0] == 56
                     and task["role"] in (0,1) and self.case_id in (20,21), "birth_event")
                child_pid = struct.unpack("<Q", unhex(event["raw"]["event_message"], size=8))[0]
                role = task["role"] + 1
                need(child_pid != pid and role not in self.roles and self.births == role-1, "birth_order")
                need(child_pid in self.tasks, "birth_child_not_acquired")
                child = self.tasks[child_pid]
                need(child["role"] is None and child["parent"] is None, "birth_duplicate")
                need(int(child["last_status"]["PPid"]) == pid
                     and int(child["last_status"]["TracerPid"]) == self.observer_pid, "birth_child_identity")
                parent_ns = task["last_status"].get("NSpid", "").split()
                child_ns = child["last_status"].get("NSpid", "").split()
                need(parent_ns and child_ns and
                     all(re.fullmatch(r"[0-9]+",item) for item in (*parent_ns,*child_ns))
                     and int(parent_ns[0]) == pid and int(child_ns[0]) == child_pid,
                     "birth_namespace_pid_fields")
                if role == 1:
                    need(len(child_ns) == len(parent_ns)+1 and int(child_ns[-1]) == 1,
                         "birth_new_pid_namespace")
                else:
                    need(len(child_ns) == len(parent_ns) and int(parent_ns[-1]) == 1
                         and int(child_ns[-1]) > 1,"birth_same_pid_namespace")
                child.update(role=role, parent=pid, guard=True, filter_count=task["filter_count"],
                             ctid=task["ctid"] if role == 2 else None)
                child["execs"] = 1
                child["newborn_return"] = True
                child["entry"] = task["entry"]
                task["clone_child"] = child_pid
                self.roles[role] = child_pid
                self.births += 1
                return
            if event_id == 0 and sig == 17:
                need(self.case_id == 20 and task["role"] in (0,1) and task["clone_child"] is not None
                     and not task["sigchld_seen"] and task["clone_result"] is not None, "sigchld_role_or_count")
                info = unhex(event["raw"]["siginfo"],size=128)
                signum,error,code = struct.unpack_from("<iii",info)
                child,uid,child_status = struct.unpack_from("<iIi",info,16)
                need(signum == 17 and error == 0 and code in (2,3)
                     and child == task["clone_result"] and child_status == 31, "sigchld_identity")
                task["sigchld_seen"] = True
                task["pending_signal"] = 17
                if task["wait4_restart_args"] is not None:
                    task["restart_signal_seen"] = True
                return
            need(event_id == 0 and sig == 133, "unexpected_trace_stop")
            info = syscall_info(unhex(event["raw"]["syscall_info"], size=None))
            need(info["ip"] == regs[16] and info["sp"] == regs[19], "syscall_register_disagreement")
            if info["op"] == 1:
                need(info["number"] == regs[15], "syscall_number_disagreement")
                if info["arch"] == ARCH:
                    need(info["args"] == tuple(regs[i] for i in (14,13,12,7,9,8)), "syscall_argument_disagreement")
                elif info["arch"] == 0x40000003:
                    need(info["args"] == tuple(regs[i] & 0xffffffff for i in (5,11,12,13,14,4)),
                         "compat_argument_disagreement")
                self._entry(event, task, info, fields)
            elif info["op"] == 2:
                need((info["result"] & U64) == regs[10], "syscall_result_disagreement")
                self._exit(event, task, info)
            else:
                need(False, "syscall_stop_op")
        else:
            need(status & 0xff != 0xff and (status & 127 == 0 or 0 < status & 127 < 127), "terminal_wait")
            if not self.cleanup:
                need(not task["stopped"] and not task["terminal"] and task["entry"] is not None,
                     "natural_terminal_without_restart")
                if self.case_id == 1:
                    need(pid == self.roles.get(0) and task["control"] and status == 0
                         and task["entry"] == (60,(0,)*6,ARCH), "control_exit")
                else:
                    need(task["negative"] and status & 127 == 31, "negative_exit")
            elif self.case_id == 21 and not self.failure:
                need(status & 127 == 9 and pid in self.signals, "cancel_exit_without_owned_signal")
            task["terminal"].append(status)
            need(len(task["terminal"]) <= 3, "terminal_wait_count")
            task["stopped"] = False
        self.terminal_ready = (len(self.roles) == 3 and all(self.tasks[pid]["park"] for pid in self.roles.values())) if self.case_id == 21 else (
            len(self.roles) == (3 if self.case_id == 20 else 1) and all(self.tasks[pid]["terminal"] for pid in self.roles.values()))

    def consume(self, event):
        try:
            return self._consume(event)
        except QualificationError:
            raise
        except (KeyError, IndexError, TypeError, ValueError, OverflowError, UnicodeError, struct.error) as exc:
            raise QualificationError("containment_guard_qualification_event_invalid") from exc

    def _consume(self, event):
        need(not self.drained,"event_after_wait_drained")
        need(type(event) is dict and event.get("seq") == self.seq and self.seq < 8192, "event_sequence")
        at = integer(event.get("t_ns"), "event_time", self.time)
        op = event.get("op")
        validate_event_structure(event)
        if op == "spawn":
            need(not self.tasks and not self.cleanup, "spawn_order")
            self._own(event, 0)
        elif op == "acquire":
            need(not self.cleanup and self.case_id in (20,21), "acquire_order")
            self._own(event)
        elif op == "seize":
            task = self._task(event["pid"])
            need(not task["seized"] and task["role"] == 0 and event["options"] == PTRACE_OPTIONS, "seize_options")
            task["seized"] = True
        elif op == "interrupt":
            task = self._task(event["pid"])
            need(task["seized"] and not task["interrupted"] and not task["stopped"], "interrupt_order")
            task["interrupted"] = True
        elif op == "release":
            task = self._task(event["pid"])
            need(task["role"] == 0 and task["stopped"] and task["interrupt_consumed"]
                 and self.releases == 0 and not self.cleanup, "release_before_stop")
            self.releases = 1
        elif op == "resume":
            task = self._task(event["pid"])
            need(type(event["signal"]) is int and event["signal"] == task["pending_signal"]
                 and self.can_resume(event["pid"], event["request"]), "restart_forbidden")
            task["stopped"] = False
            if event["signal"] == 17 and task["wait4_restart_args"] is not None:
                task["restart_signal_forwarded"] = True
            task["pending_signal"] = 0
        elif op == "wait":
            self._wait(event)
        elif op == "cleanup_begin":
            need(not self.cleanup and event["reason"] in ("normal","failure"), "cleanup_order")
            need(event["reason"] == "failure" or self.terminal_ready, "premature_cleanup")
            self.failure |= event["reason"] == "failure"
            self.cleanup = True
        elif op == "pidfd_signal":
            task = self._task(event["pid"])
            need(self.cleanup and event["pidfd"] == task["pidfd"] and event["signal"] == 9
                 and event["result"] in (0,-1) and type(event["result"]) is int
                 and type(event["errno"]) is int and 0 <= event["errno"] <= 4095, "cleanup_signal")
            need(event["pid"] not in self.signals, "cleanup_signal_retry")
            expected = sorted((t for t in self.tasks.values() if not t["terminal"]), key=lambda t:t["role"] if t["role"] is not None else 3, reverse=True)
            remaining = [t["pid"] for t in expected if t["pid"] not in self.signals]
            need(remaining and event["pid"] == remaining[0], "cleanup_signal_order")
            self.signals.append(event["pid"])
            if event["result"] != 0 or event["errno"] != 0:
                self.failure = True
        elif op == "pidfd_poll":
            task = self._task(event["pid"])
            need(self.cleanup and event["pidfd"] == task["pidfd"], "cleanup_poll_identity")
            mask = integer(event["revents"], "poll_mask", 0, 65535)
            need(mask & ~(1|16) == 0, "poll_error")
            if mask & 16:
                need(task["terminal"], "hangup_without_terminal")
                task["hup"] = True
        elif op == "wait_drained":
            need(self.cleanup and event["errno"] == 10 and all(t["terminal"] and t["hup"] for t in self.tasks.values())
                 and not self.pending, "cleanup_not_drained")
            self.drained = True
        elif op == "failure":
            need(type(event["code"]) is str and _CODE.fullmatch(event["code"])
                 and type(event["errno"]) is int and 0 <= event["errno"] <= 4095, "failure_fields")
            self.failure = True
        self.seq += 1
        self.time = at
        self.finished = bool(self.cleanup and self.drained and not self.failure and self.terminal_ready)
        return self


def verify_probe_elf(raw, *, expected_probe_sha256):
    """Inspect an externally selected executable as bytes; never run or build it."""
    digest(expected_probe_sha256)
    need(type(raw) is bytes and 64 <= len(raw) <= 262144 and binding(raw)["sha256"] == expected_probe_sha256, "probe_binding")
    need(raw[:16] == b"\x7fELF\x02\x01\x01" + b"\0" * 9, "probe_ident")
    values = struct.unpack_from("<HHIQQQIHHHHHH", raw, 16)
    kind, machine, version, entry, phoff, shoff, flags, ehsize, phsize, phnum, shsize, shnum, shstr = values
    need((kind,machine,version,flags,ehsize,phsize,shsize) == (2,62,1,0,64,56,64)
         and 1 <= phnum <= 32 and 1 <= shnum <= 256 and 0 < shstr < shnum
         and phoff + phnum*56 <= len(raw) and shoff + shnum*64 <= len(raw), "probe_elf_header")
    loads, stacks = [], 0
    for index in range(phnum):
        ptype,pflags,off,address,_physical,filesz,memsz,align = struct.unpack_from("<IIQQQQQQ", raw, phoff+index*56)
        need(ptype not in (2,3,7), "probe_dynamic_or_tls")
        if ptype == 0x6474e551:
            need(pflags == 6 and memsz == 0 and filesz == 0, "probe_stack")
            stacks += 1
        if ptype == 1:
            need(pflags & ~7 == 0 and pflags & 4 != 0, "probe_load_flags")
            need(not (pflags & 1 and pflags & 2) and 0 <= off <= len(raw) and filesz <= memsz
                 and off+filesz <= len(raw) and address+memsz <= U64
                 and align == 4096 and off % 4096 == address % 4096, "probe_load_extent")
            low, high = address & ~4095, (address + memsz + 4095) & ~4095
            need(all(high <= item[0] or item[1] <= low for item in loads), "probe_page_overlap")
            loads.append((low,high,pflags,address,off,filesz,memsz))
    need(stacks == 1 and loads and sum(bool(p[2]&1 and p[3] <= entry < p[3]+p[5]) for p in loads) == 1,
         "probe_entry_mapping")
    sections = [struct.unpack_from("<IIQQQQIIQQ", raw, shoff+i*64) for i in range(shnum)]
    string = sections[shstr]
    need(string[1] == 3 and string[4]+string[5] <= len(raw), "probe_section_strings")
    names = raw[string[4]:string[4]+string[5]]
    guard = []
    for section in sections:
        name,stype,sflags,address,offset,size,_link,_info,_alignment,_entsize = section
        need(name < len(names), "probe_section_name")
        stop = names.find(b"\0",name)
        need(stop >= 0, "probe_section_name")
        if names[name:stop] == b".pulse_task_guard":
            need(stype == 1 and sflags == 2 and size == 272 and offset+size <= len(raw)
                 and raw[offset:offset+size] == GUARD_BYTES, "probe_guard_section")
            selected = [p for p in loads if not p[2]&2 and p[3] <= address and address+size <= p[3]+p[5]
                        and p[4]+address-p[3] == offset]
            need(len(selected) == 1, "probe_guard_mapping")
            guard.append(section)
    need(len(guard) == 1, "probe_guard_roster")
    return {"probe": binding(raw), "elf_shape_verified": True, "guard_section_verified": True,
            "guard_address": guard[0][3], "source_binary_equivalence_verified": False, "build_authenticated": False}


NAMESPACE_NAMES = ("cgroup","ipc","mnt","net","pid","pid_for_children","time","time_for_children","user","uts")


def validate_environment(value):
    keys(value, ("uname","boot_id","observer_executable","python_version","ids","security","lsm_label_hex","namespaces"), "environment_shape")
    keys(value["uname"], ("sysname","release","version","machine"), "uname_shape")
    need(value["uname"]["sysname"] == "Linux" and value["uname"]["machine"] == "x86_64"
         and all(type(v) is str and 0 < len(v) <= 256 for v in value["uname"].values()), "environment_platform")
    need(type(value["boot_id"]) is str and re.fullmatch(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}",value["boot_id"]), "boot_id")
    keys(value["observer_executable"], ("size_bytes","sha256"), "observer_executable")
    integer(value["observer_executable"]["size_bytes"],"observer_executable_size",1,67108864)
    digest(value["observer_executable"]["sha256"])
    need(type(value["python_version"]) is list and len(value["python_version"]) == 3
         and all(type(n) is int and 0 <= n <= 100 for n in value["python_version"]), "python_version")
    keys(value["ids"], ("uid","euid","gid","egid"), "environment_ids")
    need(all(type(n) is int and 0 < n < (1<<32) for n in value["ids"].values())
         and value["ids"]["uid"] == value["ids"]["euid"]
         and value["ids"]["gid"] == value["ids"]["egid"], "environment_nonroot")
    security = value["security"]
    keys(security, ("NoNewPrivs","Seccomp","Seccomp_filters","CapEff","CapPrm","CapInh","CapBnd","CapAmb"), "environment_security")
    for name in ("NoNewPrivs","Seccomp","Seccomp_filters"):
        integer(security[name],"environment_security_value",0,65535)
    need(security["NoNewPrivs"] in (0,1) and security["Seccomp"] in (0,2), "environment_security_value")
    for name in ("CapEff","CapPrm","CapInh","CapBnd","CapAmb"):
        need(type(security[name]) is str and re.fullmatch(r"[0-9a-f]{16}",security[name]), "environment_capability")
        if name in ("CapEff","CapPrm","CapInh"):
            need(int(security[name],16) == 0, "environment_capabilities_nonzero")
    unhex(value["lsm_label_hex"],65536,empty=True)
    keys(value["namespaces"],NAMESPACE_NAMES,"environment_namespaces")
    for name, link in value["namespaces"].items():
        if name in ("time","time_for_children") and link is None:
            continue
        prefix = name.removesuffix("_for_children")
        need(type(link) is str and re.fullmatch(re.escape(prefix)+r":\[[1-9][0-9]*\]",link),"environment_namespace")
    need((value["namespaces"]["time"] is None) == (value["namespaces"]["time_for_children"] is None),"environment_time_namespace")


def _observer(value, environment, complete):
    keys(value,("pid","stat_hex","status_hex","sigaction_hex","subreaper_before","subreaper_after","subreaper_restored"),"observer_shape")
    pid = integer(value["pid"],"observer_pid",2,2147483647)
    stat = parse_stat(unhex(value["stat_hex"]))
    status = parse_status(unhex(value["status_hex"]))
    need(stat["pid"] == pid and stat["threads"] == 1 and stat["starttime"] > 0
         and int(status["Pid"]) == pid and int(status["Tgid"]) == pid
         and int(status["Threads"]) == 1 and int(status["TracerPid"]) == 0,"observer_identity")
    _initial_credentials(status)
    if environment is not None:
        for label,name in (("Uid","uid"),("Gid","gid")):
            need(int(status[label].split()[0]) == environment["ids"][name],"observer_environment_ids")
        for name in environment["security"]:
            if name in ("NoNewPrivs","Seccomp","Seccomp_filters"):
                need(int(status[name]) == environment["security"][name],"observer_environment_security")
            else:
                need(status.get(name) == environment["security"][name],"observer_environment_security")
    action = unhex(value["sigaction_hex"],size=152)
    need(struct.unpack_from("<Q",action)[0] == 0 and struct.unpack_from("<I",action,136)[0] & 2 == 0,
         "observer_sigchld_disposition")
    need(type(value["subreaper_before"]) is int and value["subreaper_before"] in (0,1)
         and value["subreaper_after"] == 1 and type(value["subreaper_after"]) is int,"observer_subreaper")
    if complete:
        same(value["subreaper_restored"],value["subreaper_before"],"observer_subreaper_restore")
    else:
        need(value["subreaper_restored"] is None or type(value["subreaper_restored"]) is int
             and value["subreaper_restored"] in (0,1),"observer_subreaper_restore")
    return pid


def _failure_value(value, *, optional=False):
    need(optional and value is None or type(value) is str and _CODE.fullmatch(value), "failure_code")


def _failures(values):
    need(type(values) is list and len(values) <= 64,"cleanup_failures")
    for value in values:
        _failure_value(value)


def verify_record(*, record_bytes, expected_record_sha256, expected_probe_sha256,
                  expected_environment_sha256, source_inputs=None):
    """Verify a complete native/scripted record or preserve an incomplete prefix.

    External expected digests are required even for native evidence. The origin
    label describes the reviewed producer path; this byte checker cannot prove
    physical provenance or prevent someone from fabricating an entire record.
    """
    try:
        digest(expected_record_sha256)
        digest(expected_probe_sha256)
        digest(expected_environment_sha256)
        need(binding(record_bytes)["sha256"] == expected_record_sha256,"record_digest_mismatch")
        value = parse(record_bytes)
        keys(value,("record_type","profile","evidence_origin","attempt_id","status","failure","cleanup_failures",
                    "probe","environment","environment_after","observer","sources","sources_after","limits","boundary","timing","cases"),"record_shape")
        same(value["record_type"],RECORD_TYPE,"record_type")
        same(value["profile"],PROFILE,"profile")
        same(value["limits"],LIMITS,"limits")
        same(value["boundary"],BOUNDARY,"boundary")
        need(value["evidence_origin"] in ("native_owned_probe","scripted_test_backend"),"evidence_origin")
        need(type(value["attempt_id"]) is str and re.fullmatch(r"[0-9a-f]{32}",value["attempt_id"]),"attempt_id")
        complete = value["status"] == "completed"
        need(value["status"] in ("completed","incomplete"),"record_status")
        _failure_value(value["failure"],optional=True)
        _failures(value["cleanup_failures"])
        need((value["failure"] is None and not value["cleanup_failures"]) if complete else value["failure"] is not None,"failure_status")
        keys(value["probe"],("size_bytes","sha256","hex"),"probe_shape")
        probe = unhex(value["probe"]["hex"],262144)
        same({key:value["probe"][key] for key in ("size_bytes","sha256")},binding(probe),"probe_descriptor")
        verify_probe_elf(probe,expected_probe_sha256=expected_probe_sha256)
        if value["environment"] is not None:
            validate_environment(value["environment"])
            need(binding(canonical(value["environment"]))["sha256"] == expected_environment_sha256,"environment_selection")
        else:
            need(not complete,"missing_environment")
        if value["environment_after"] is not None:
            validate_environment(value["environment_after"])
        if complete:
            same(value["environment_after"],value["environment"],"environment_changed")
        sources = source_bytes() if source_inputs is None else dict(source_inputs)
        inventory = source_inventory(inputs=sources)
        same(value["sources"],inventory,"source_selection")
        if complete:
            same(value["sources_after"],inventory,"sources_changed")
            verify_prerequisite_source_contract()
        elif value["sources_after"] is not None:
            source_inventory(inputs=sources)
        observer_pid = _observer(value["observer"],value["environment"],complete) if value["observer"] is not None else None
        need(observer_pid is not None or not complete,"missing_observer")
        keys(value["timing"],("started_ns","finished_ns"),"timing_shape")
        start = integer(value["timing"]["started_ns"],"started_ns",1)
        finish = integer(value["timing"]["finished_ns"],"finished_ns",start)
        need(type(value["cases"]) is list and len(value["cases"]) <= 21,"case_roster")
        if complete:
            need(len(value["cases"]) == 21,"case_count")
        total_events, observation_ns, previous, states = 0, 0, start, []
        for index, case in enumerate(value["cases"],1):
            keys(case,("case_id","started_ns","finished_ns","failure","cleanup_failures","unresolved_tasks","stdout_hex","stderr_hex","events"),"case_shape")
            same(case["case_id"],index,"case_order")
            begun = integer(case["started_ns"],"case_started",previous,finish)
            ended = integer(case["finished_ns"],"case_finished",begun,finish)
            _failure_value(case["failure"],optional=True)
            _failures(case["cleanup_failures"])
            need(type(case["unresolved_tasks"]) is list and len(case["unresolved_tasks"]) <= 4, "unresolved_tasks")
            unresolved = set()
            for item in case["unresolved_tasks"]:
                keys(item,("pid","pidfd","terminal","hangup"),"unresolved_task_shape")
                pid = integer(item["pid"],"unresolved_pid",2,2147483647)
                need(pid not in unresolved,"unresolved_duplicate")
                unresolved.add(pid)
                need(item["pidfd"] is None or type(item["pidfd"]) is int and 3 <= item["pidfd"] < (1<<20),"unresolved_pidfd")
                need(type(item["terminal"]) is bool and type(item["hangup"]) is bool,"unresolved_state")
            out = unhex(case["stdout_hex"],4096,empty=True)
            err = unhex(case["stderr_hex"],4096,empty=True)
            need(type(case["events"]) is list and len(case["events"]) <= 8192,"case_events")
            total_events += len(case["events"])
            need(total_events <= 65536,"events_total")
            if complete:
                need(case["failure"] is None and case["cleanup_failures"] == [] and case["unresolved_tasks"] == [] and not out and not err,"complete_case_failure_or_output")
            state = TraceState(index,observer_pid,probe) if observer_pid is not None else None
            cleanup_at = None
            event_previous = begun
            for event_index, event in enumerate(case["events"]):
                need(type(event) is dict and type(event.get("t_ns")) is int and event_previous <= event["t_ns"] <= ended,"event_case_time")
                event_previous = event["t_ns"]
                if event.get("op") == "cleanup_begin" and cleanup_at is None:
                    cleanup_at = event["t_ns"]
                if complete:
                    state.consume(event)
                else:
                    # A failed acquisition can have a final failed operation or
                    # unjoined child. Preserve bounded bytes; never promote it
                    # to the complete state machine or native qualification.
                    need(event.get("seq") == event_index,"incomplete_event_sequence")
                    validate_event_structure(event)
                    need(event.get("op") in ("spawn","acquire","seize","interrupt","release","wait","resume","cleanup_begin","pidfd_signal","pidfd_poll","wait_drained","failure"),"incomplete_event_operation")
            if complete:
                need(state.finished and cleanup_at is not None,"case_not_finished")
                need(cleanup_at-begun <= 5_000_000_000 and ended-cleanup_at <= 5_000_000_000,"case_deadline")
                observation_ns += cleanup_at-begun
                states.append(state)
            previous = ended
        if complete:
            need(observation_ns <= 120_000_000_000 and finish-start <= 225_000_000_000,"suite_deadline")
        if source_inputs is None:
            need(source_bytes() == sources,"sources_changed_during_check")
        native = complete and value["evidence_origin"] == "native_owned_probe"
        return {"record_type":REPORT_TYPE,"profile":PROFILE,
                "status":"accepted_native_guard_probe_record" if native else
                         "accepted_scripted_guard_probe_record" if complete else "preserved_incomplete",
                "record":binding(record_bytes),"probe":binding(probe),
                "environment_sha256":expected_environment_sha256,"sources":inventory,
                "prerequisite_source_contract_verified":complete,
                "complete_guard_probe_sequence_verified":complete,"native_guard_probe_record_verified":native,
                "case_count":len(value["cases"]),"observed_guard_program":binding(GUARD_BYTES),
                "evidence_basis":"source_bound_probe_and_reconstructed_raw_observer_transcript",
                **BOUNDARY}
    except QualificationError:
        raise
    except (KeyError,IndexError,TypeError,ValueError,OverflowError,UnicodeError,struct.error) as exc:
        raise QualificationError("containment_guard_qualification_invalid_record") from exc


def _write_new(path, raw):
    """Create one file under pinned non-symlink directories; never replace it."""
    need(type(raw) is bytes and len(raw) <= 33554432,"output_extent")
    path = Path(path).absolute()
    opened = []
    try:
        directory = os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
        opened.append(directory)
        for part in path.parts[1:-1]:
            directory = os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW,dir_fd=directory)
            opened.append(directory)
        fd = os.open(path.name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC|os.O_NOFOLLOW,0o600,dir_fd=directory)
        opened.append(fd)
        before = os.fstat(fd)
        need(before.st_nlink == 1 and (before.st_mode & 0o170000) == 0o100000,"output_identity")
        rest = memoryview(raw)
        while rest:
            count = os.write(fd,rest)
            need(count > 0,"output_short_write")
            rest = rest[count:]
        os.fsync(fd)
        need(os.pread(fd,len(raw)+1,0) == raw,"output_bytes_changed")
        current = os.stat(path.name,dir_fd=directory,follow_symlinks=False)
        after = os.fstat(fd)
        need((current.st_dev,current.st_ino,current.st_nlink,current.st_size) ==
             (before.st_dev,before.st_ino,1,len(raw)) and
             (after.st_dev,after.st_ino,after.st_nlink,after.st_size) ==
             (before.st_dev,before.st_ino,1,len(raw)),"output_replaced")
    finally:
        for fd in reversed(opened):
            os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record",type=Path,required=True)
    parser.add_argument("--expected-record-sha256",required=True)
    parser.add_argument("--expected-probe-sha256",required=True)
    parser.add_argument("--expected-environment-sha256",required=True)
    parser.add_argument("--out",type=Path,required=True)
    args = parser.parse_args(argv)
    try:
        report = verify_record(record_bytes=_read(args.record,33554432),
            expected_record_sha256=args.expected_record_sha256,
            expected_probe_sha256=args.expected_probe_sha256,
            expected_environment_sha256=args.expected_environment_sha256)
        _write_new(args.out,canonical(report))
    except (OSError,QualificationError) as exc:
        print(getattr(exc,"code","containment_guard_qualification_io"),file=sys.stderr)
        return 1
    return 0 if report["complete_guard_probe_sequence_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
