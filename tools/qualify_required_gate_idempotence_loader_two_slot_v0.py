#!/usr/bin/env python3
"""Collect a bounded, owned two-slot hardware qualification record.

This command executes only the fixed 138-byte capability probe.  It never
executes an original PULSE subject, repairs registers or supplies build trust.
The default backend performs a native attempt only when this command is invoked;
an explicitly supplied backend is always labelled ``scripted_test_backend``.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import fcntl
import hashlib
import os
from pathlib import Path
import re
import resource
import signal
import stat
import struct
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_loader_two_slot_qualification_v0 as checker


PTRACE_TRACEME, PTRACE_PEEKUSER, PTRACE_POKEUSER = 0, 3, 6
PTRACE_CONT, PTRACE_GETREGS = 7, 12
PTRACE_SETOPTIONS, PTRACE_GETEVENTMSG, PTRACE_GETSIGINFO = 0x4200, 0x4201, 0x4202
PTRACE_OPTIONS = 0x10001E
DEBUGREG_OFFSET = 848
DR6_RESERVED = 0xFFFF0FF0
SLOT0_TARGET, SLOT1_TARGET, PROBE_ENTRY = 0x400085, 0x400088, 0x400080
OBSERVATION_NS, CLEANUP_NS = 15_000_000_000, 2_000_000_000
FULL_SEALS = 15
READ_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
DIRECTORY_FLAGS = READ_FLAGS | os.O_DIRECTORY
NAMESPACE_NAMES = ("cgroup", "ipc", "mnt", "net", "pid", "pid_for_children",
                   "time", "time_for_children", "user", "uts")


class QualificationError(ValueError):
    """Stable public failure code; raw exception text is never published."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise QualificationError(code)


def _failure(exc):
    if isinstance(exc, OSError):
        return "two_slot_native_os_error_" + str(max(0, min(exc.errno or 0, 4095)))
    code = getattr(exc, "code", None)
    if type(code) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", code):
        return code
    return "two_slot_native_interrupted" if not isinstance(exc, Exception) else "two_slot_native_failure"


def _error_number(exc):
    return max(0, min(getattr(exc, "errno", 0) or 0, 4095))


def _preserve_raw_failure(exc, raw, maximum):
    """Carry bounded acquired bytes across a failed read, never a truncation.

    Only the controller's normal raw-roster and aggregate-budget checks may
    publish these bytes. Their enclosing failure remains a failure; an acquired
    prefix never becomes a successful full-file or full-memory observation.
    """
    if raw is not None and 0 < len(raw) <= maximum <= 65536:
        exc.raw_bytes = bytes(raw)
    return exc


class NativeBackend:
    """Small Linux/x86-64 backend; no generalized ptrace write interface."""

    def __init__(self):
        self.observer_pid = os.getpid()
        self.child_pid = self.starttime = self.pidfd = self.procfd = None
        self.probe_fd = self.observerfd = None
        self.probe_seals = self.probe_mode = None
        self.unexpected_children = []
        self.cleanup_operations = []
        self.reaped = False
        self.last_wait = None
        self.last_event_message = None
        self.libc = ctypes.CDLL(None, use_errno=True)
        self.libc.ptrace.argtypes = (ctypes.c_ulong, ctypes.c_ulong,
                                    ctypes.c_void_p, ctypes.c_void_p)
        self.libc.ptrace.restype = ctypes.c_long
        self.libc.prctl.argtypes = (ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                                   ctypes.c_ulong, ctypes.c_ulong)
        self.libc.prctl.restype = ctypes.c_int

    def clock(self):
        return time.monotonic_ns()

    def _deadline(self, deadline):
        if deadline is not None:
            _need(self.clock() < deadline, "two_slot_native_deadline")

    def _read_fd(self, fd, maximum, deadline=None):
        result = bytearray()
        try:
            before = os.fstat(fd)
            _need(stat.S_ISREG(before.st_mode), "two_slot_native_regular_file")
            while True:
                self._deadline(deadline)
                chunk = os.read(fd, min(65536, maximum + 1 - len(result)))
                if not chunk:
                    break
                result.extend(chunk)
                _need(len(result) <= maximum, "two_slot_native_read_limit")
            after = os.fstat(fd)
            _need((before.st_dev, before.st_ino, before.st_mode, before.st_size) ==
                  (after.st_dev, after.st_ino, after.st_mode, after.st_size),
                  "two_slot_native_file_identity_changed")
            self._deadline(deadline)
            return bytes(result)
        except BaseException as exc:
            _preserve_raw_failure(exc, result, maximum)
            raise

    def _read_path(self, path, maximum, deadline=None, *, follow=False, directory=None):
        flags = os.O_RDONLY | os.O_CLOEXEC | (0 if follow else os.O_NOFOLLOW)
        fd = os.open(path, flags, dir_fd=directory)
        raw, failure = None, None
        try:
            raw = self._read_fd(fd, maximum, deadline)
            return raw
        except BaseException as exc:
            failure = exc
            raise
        finally:
            try:
                os.close(fd)
            except BaseException as exc:
                if failure is None:
                    _preserve_raw_failure(exc, raw, maximum)
                    raise

    def _platform(self):
        _need(sys.platform == "linux" and os.uname().machine == "x86_64"
              and ctypes.sizeof(ctypes.c_ulong) == 8
              and os.sysconf("SC_PAGE_SIZE") == 4096
              and 2 <= self.observer_pid < (1 << 31),
              "two_slot_native_platform")
        # An ignored/custom SIGCHLD handler could reap a child behind this
        # controller and invalidate the owned-unreaped-PID cleanup fallback.
        # Reject that caller state; never replace its signal handler.
        _need(signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL,
              "two_slot_native_sigchld_handler")
        # Keep every newly allocated control/probe descriptor outside stdio.
        # A closed stdio slot must not be reused for the memfd and overwritten
        # by the child's fixed /dev/null setup.
        for descriptor in (0, 1, 2):
            os.fstat(descriptor)
        _need(os.listdir("/proc/self/task") == [str(self.observer_pid)],
              "two_slot_native_observer_threads")

    def context(self):
        self._platform()
        if self.observerfd is None:
            self.observerfd = os.open("/proc/" + str(self.observer_pid), DIRECTORY_FLAGS)
        uname = os.uname()
        namespaces = {}
        for name in NAMESPACE_NAMES:
            try:
                namespaces[name] = os.readlink("ns/" + name, dir_fd=self.observerfd)
            except FileNotFoundError:
                if name not in ("time", "time_for_children"):
                    raise
                namespaces[name] = None
        executable = self._read_path("exe", 64 * 1024 * 1024, follow=True,
                                     directory=self.observerfd)
        return {
            "uname": {key: getattr(uname, key) for key in ("sysname", "release", "version", "machine")},
            "boot_id": self._read_path("/proc/sys/kernel/random/boot_id", 128).decode("ascii").strip(),
            "observer": checker.binding(executable), "namespaces": namespaces,
        }

    def source_inventory(self):
        return checker.source_inventory()

    def snapshot(self):
        return {"process": {"observer_pid": self.observer_pid, "child_pid": self.child_pid,
                            "starttime": self.starttime, "pidfd": self.pidfd,
                            "proc_dir_pinned": self.procfd is not None,
                            "unexpected_children": [dict(row) for row in self.unexpected_children]},
                "probe": {"seals": self.probe_seals, "mode": self.probe_mode}}

    def _ptrace(self, request, pid, address=0, data=0):
        allowed = {PTRACE_TRACEME, PTRACE_PEEKUSER, PTRACE_POKEUSER, PTRACE_CONT,
                   PTRACE_GETREGS, PTRACE_SETOPTIONS, PTRACE_GETEVENTMSG, PTRACE_GETSIGINFO}
        _need(type(request) is int and request in allowed, "two_slot_native_ptrace_forbidden")
        _need(type(pid) is int and pid >= 0 and type(address) is int and type(data) is int,
              "two_slot_native_ptrace_arguments")
        if request == PTRACE_TRACEME:
            _need(pid == address == data == 0, "two_slot_native_traceme_arguments")
        else:
            _need(pid > 0 and pid == self.child_pid, "two_slot_native_ptrace_pid")
        if request == PTRACE_PEEKUSER:
            _need(address in {DEBUGREG_OFFSET + 8 * n for n in (0, 1, 2, 3, 6, 7)}
                  and data == 0, "two_slot_native_debug_read_forbidden")
        elif request == PTRACE_POKEUSER:
            choices = {DEBUGREG_OFFSET: SLOT0_TARGET, DEBUGREG_OFFSET + 8: SLOT1_TARGET,
                       DEBUGREG_OFFSET + 48: DR6_RESERVED, DEBUGREG_OFFSET + 56: 5}
            _need(address in choices and data == choices[address],
                  "two_slot_native_debug_write_forbidden")
        elif request == PTRACE_SETOPTIONS:
            _need(address == 0 and data == PTRACE_OPTIONS, "two_slot_native_options_forbidden")
        elif request == PTRACE_CONT:
            _need(address == data == 0, "two_slot_native_continue_forbidden")
        elif request in (PTRACE_GETREGS, PTRACE_GETSIGINFO, PTRACE_GETEVENTMSG):
            _need(address == 0 and data > 0, "two_slot_native_read_buffer")
        ctypes.set_errno(0)
        result = self.libc.ptrace(request, pid, address, data)
        number = ctypes.get_errno()
        if result == -1 and number:
            raise OSError(number, "ptrace request failed")
        if request == PTRACE_PEEKUSER:
            return result & ((1 << 64) - 1)
        _need(result == 0, "two_slot_native_ptrace_return")
        return result

    def _child(self, inherited):
        try:
            nullfd = os.open("/dev/null", os.O_RDWR | os.O_CLOEXEC)
            for target in (0, 1, 2):
                os.dup2(nullfd, target)
            for candidate in (*inherited, nullfd):
                if candidate > 2 and candidate != self.probe_fd:
                    try:
                        os.close(candidate)
                    except OSError as exc:
                        if exc.errno != errno.EBADF:
                            raise
            os.setsid()
            os.chdir("/")
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            ctypes.set_errno(0)
            _need(self.libc.prctl(1, signal.SIGKILL, 0, 0, 0) == 0
                  and os.getppid() == self.observer_pid, "two_slot_native_parent_guard")
            self._ptrace(PTRACE_TRACEME, 0)
            os.kill(os.getpid(), signal.SIGSTOP)
            os.execve("/proc/self/fd/" + str(self.probe_fd), ["pulse-two-slot-probe"],
                      {"LC_ALL": "C", "TZ": "UTC"})
        except OSError as exc:
            os._exit(160 + min(max(exc.errno or 0, 0), 63))
        except BaseException:
            os._exit(120)

    def spawn(self, probe, deadline):
        self._platform()
        self._deadline(deadline)
        _need(probe == checker.probe_bytes(), "two_slot_native_probe_selection")
        self.probe_fd = os.memfd_create("pulse-two-slot-probe-v0",
                                       os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        remaining = memoryview(probe)
        while remaining:
            self._deadline(deadline)
            count = os.write(self.probe_fd, remaining)
            _need(count > 0, "two_slot_native_probe_write")
            remaining = remaining[count:]
        os.fchmod(self.probe_fd, 0o500)
        fcntl.fcntl(self.probe_fd, fcntl.F_ADD_SEALS, FULL_SEALS)
        self.probe_seals = fcntl.fcntl(self.probe_fd, fcntl.F_GET_SEALS)
        self.probe_mode = stat.S_IMODE(os.fstat(self.probe_fd).st_mode)
        _need(self.probe_seals == FULL_SEALS and self.probe_mode == 0o500
              and os.pread(self.probe_fd, len(probe) + 1, 0) == probe,
              "two_slot_native_probe_seals")
        inherited = tuple(int(name) for name in os.listdir("/proc/self/fd"))
        self._deadline(deadline)
        pid = os.fork()
        if pid == 0:
            self._child(inherited)
            os._exit(122)
        self.child_pid = pid  # Ownership exists even if either descriptor open fails.
        self.pidfd = os.pidfd_open(pid, 0)
        self.procfd = os.open("/proc/" + str(pid), DIRECTORY_FLAGS)
        return self.snapshot()["process"]

    def wait(self, deadline):
        _need(self.child_pid is not None and not self.reaped, "two_slot_native_wait_ownership")
        self.last_wait = None
        while True:
            self._deadline(deadline)
            try:
                pid, status = os.waitpid(self.child_pid, os.WNOHANG | os.WUNTRACED)
            except InterruptedError:
                continue
            if pid:
                self.last_wait = (pid, status)
                if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                    self.reaped = True
                event = status >> 16 if os.WIFSTOPPED(status) else 0
                if event in (1, 2, 3):
                    word = ctypes.c_ulong()
                    self._ptrace(PTRACE_GETEVENTMSG, self.child_pid, 0, ctypes.addressof(word))
                    new_pid = word.value
                    self.last_event_message = new_pid
                    _need(0 < new_pid < (1 << 31) and new_pid != self.child_pid
                          and not self.unexpected_children, "two_slot_native_unexpected_child")
                    row = {"pid": new_pid, "pidfd": None, "event": event, "reaped": False}
                    self.unexpected_children.append(row)
                    try:
                        row["pidfd"] = os.pidfd_open(new_pid, 0)
                    except OSError:
                        # Preserve the stopped event and exact auto-attached PID.
                        # Cleanup can kill this owned, unreaped task by PID.
                        pass
                return pid, status
            time.sleep(0.001)

    def read(self, name, deadline):
        self._deadline(deadline)
        _need(name in checker.complete_raw_names() | checker.INCOMPLETE_EXTRA_RAW,
              "two_slot_native_raw_name")
        if name == "probe.seals.bin":
            return struct.pack("<Q", fcntl.fcntl(self.probe_fd, fcntl.F_GET_SEALS))
        if name == "probe.mode.bin":
            return struct.pack("<Q", stat.S_IMODE(os.fstat(self.probe_fd).st_mode))
        if name == "unexpected.event_message.bin":
            _need(self.last_event_message is not None, "two_slot_native_event_message")
            return struct.pack("<Q", self.last_event_message)
        if name.startswith("observer."):
            leaf = "stat" if name == "observer.stat.bin" else "status"
            return self._read_path(leaf, 65536, deadline, directory=self.observerfd)
        if name == "child.pidfd.info.bin":
            return self._read_path("/proc/self/fdinfo/" + str(self.pidfd), 65536, deadline)
        if "child.stat" in name:
            raw = self._read_path("stat", 65536, deadline, directory=self.procfd)
            try:
                if self.starttime is None:
                    tail = raw[raw.rfind(b") ") + 2:].split()
                    _need(len(tail) == 50 and re.fullmatch(rb"[0-9]+", tail[19]) is not None,
                          "two_slot_native_stat")
                    self.starttime = int(tail[19])
            except BaseException as exc:
                _preserve_raw_failure(exc, raw, 65536)
                raise
            return raw
        if "child.status" in name:
            return self._read_path("status", 65536, deadline, directory=self.procfd)
        if name == "cp0.auxv.bin":
            return self._read_path("auxv", 65536, deadline, directory=self.procfd)
        if name == "cp0.executable.elf":
            return self._read_path("exe", len(checker.probe_bytes()), deadline, follow=True,
                                   directory=self.procfd)
        if ".regs." in name:
            buffer = (ctypes.c_uint64 * 27)()
            self._ptrace(PTRACE_GETREGS, self.child_pid, 0, ctypes.addressof(buffer))
            return bytes(buffer)
        if ".debug." in name:
            return struct.pack("<6Q", *(self._ptrace(PTRACE_PEEKUSER, self.child_pid,
                               DEBUGREG_OFFSET + 8 * n) for n in (0, 1, 2, 3, 6, 7)))
        if name.endswith(".siginfo.bin"):
            buffer = (ctypes.c_uint64 * 16)()
            self._ptrace(PTRACE_GETSIGINFO, self.child_pid, 0, ctypes.addressof(buffer))
            return bytes(buffer)
        if ".code." in name:
            fd = os.open("mem", READ_FLAGS, dir_fd=self.procfd)
            raw, failure = None, None
            try:
                raw = os.pread(fd, 10, PROBE_ENTRY)
                self._deadline(deadline)
                return raw
            except BaseException as exc:
                failure = exc
                _preserve_raw_failure(exc, raw, 10)
                raise
            finally:
                try:
                    os.close(fd)
                except BaseException as exc:
                    if failure is None:
                        _preserve_raw_failure(exc, raw, 10)
                        raise
        raise QualificationError("two_slot_native_raw_name")

    def options(self):
        return self._ptrace(PTRACE_SETOPTIONS, self.child_pid, 0, PTRACE_OPTIONS)

    def write_debug(self, number, value):
        return self._ptrace(PTRACE_POKEUSER, self.child_pid, DEBUGREG_OFFSET + 8 * number, value)

    def cont(self):
        return self._ptrace(PTRACE_CONT, self.child_pid)

    def cleanup(self, deadline):
        self.cleanup_operations = []
        targets = [row for row in self.unexpected_children if not row["reaped"]]
        if self.child_pid is not None and not self.reaped:
            targets.append({"pid": self.child_pid, "pidfd": self.pidfd, "reaped": False})
        failure = None
        for row in targets:
            op = {"op": "kill", "at_ns": self.clock(),
                  "method": "pidfd_send_signal" if row["pidfd"] is not None else "owned_pid_fallback",
                  "pid": row["pid"], "pidfd": row["pidfd"], "signal": 9,
                  "returncode": -1, "errno": 0}
            self.cleanup_operations.append(op)
            try:
                # Even late cleanup must attempt SIGKILL. Expiry prevents
                # acceptance and bounded waiting, never the owned kill itself.
                if self.clock() >= deadline:
                    failure = failure or QualificationError("two_slot_native_deadline")
                if row["pidfd"] is not None:
                    signal.pidfd_send_signal(row["pidfd"], signal.SIGKILL)
                else:
                    # This exact, unreaped fork child cannot be a reused PID.
                    os.kill(row["pid"], signal.SIGKILL)
                op["returncode"] = 0
            except BaseException as exc:
                op["errno"] = _error_number(exc)
                failure = failure or exc
                if row["pidfd"] is not None:
                    fallback = {"op": "kill", "at_ns": self.clock(),
                        "method": "owned_pid_fallback", "pid": row["pid"], "pidfd": None,
                        "signal": 9, "returncode": -1, "errno": 0}
                    self.cleanup_operations.append(fallback)
                    try:
                        # The task is a directly forked or auto-attached child
                        # that this observer has not reaped. Its PID cannot yet
                        # have been recycled. The failed pidfd operation remains
                        # a recorded failure, even if this cleanup succeeds.
                        os.kill(row["pid"], signal.SIGKILL)
                        fallback["returncode"] = 0
                    except BaseException as fallback_exc:
                        fallback["errno"] = _error_number(fallback_exc)
        for row in targets:
            try:
                while True:
                    self._deadline(deadline)
                    try:
                        pid, status = os.waitpid(row["pid"], os.WNOHANG | 0x40000000)
                    except InterruptedError:
                        continue
                    if pid:
                        _need(len(self.cleanup_operations) < 24,
                              "two_slot_native_cleanup_operation_budget")
                        self.cleanup_operations.append({"op": "wait", "at_ns": self.clock(),
                            "phase": "reap", "pid": pid, "status": status})
                        if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                            row["reaped"] = True
                            if pid == self.child_pid:
                                self.reaped = True
                            break
                        # A pending initial ptrace stop can precede SIGKILL's
                        # terminal wait. Never resume it; keep waiting boundedly.
                    else:
                        time.sleep(0.001)
            except BaseException as exc:
                failure = failure or exc
        if failure is not None:
            raise failure
        return list(self.cleanup_operations)

    def close(self):
        failure = None
        descriptors = [self.procfd, self.pidfd, self.probe_fd, self.observerfd]
        descriptors += [row["pidfd"] for row in self.unexpected_children]
        for fd in descriptors:
            if fd is not None:
                try:
                    os.close(fd)
                except BaseException as exc:
                    failure = failure or exc
        if failure is not None:
            raise failure


def _stat_identity(raw, process):
    match = re.fullmatch(rb"([0-9]+) \(([^\n]{1,64})\) (t) ([0-9 -]+)\n?", raw)
    _need(match is not None, "two_slot_native_child_stat")
    values = match.group(4).split()
    _need(len(values) == 49 and all(re.fullmatch(rb"-?[0-9]+", value) for value in values),
          "two_slot_native_child_stat")
    _need(int(match.group(1)) == process["child_pid"]
          and int(values[0]) == process["observer_pid"] and int(values[16]) == 1
          and int(values[18]) == process["starttime"], "two_slot_native_child_identity")
    return match.group(2).decode("ascii")


def _status_identity(raw, process, name):
    fields = {}
    for line in raw.decode("ascii").splitlines():
        _need(":" in line, "two_slot_native_child_status")
        key, value = line.split(":", 1)
        _need(key not in fields, "two_slot_native_status_duplicate")
        fields[key] = value.strip()
    _need(fields.get("Name") == name and fields.get("State") == "t (tracing stop)",
          "two_slot_native_child_status")
    for key, value in (("Pid", process["child_pid"]), ("Tgid", process["child_pid"]),
                       ("PPid", process["observer_pid"]), ("TracerPid", process["observer_pid"]),
                       ("NSpid", process["child_pid"]), ("Threads", 1)):
        _need(fields.get(key) == str(value), "two_slot_native_child_status_identity")


def _identity(raw, stat_name, status_name, process):
    comm = _stat_identity(bytes.fromhex(raw[stat_name]["hex"]), process)
    _status_identity(bytes.fromhex(raw[status_name]["hex"]), process, comm)


def _auxv(raw):
    _need(0 < len(raw) <= 65536 and len(raw) % 16 == 0, "two_slot_native_auxv")
    values = {}
    pairs = list(struct.iter_unpack("<QQ", raw))
    _need(pairs[-1] == (0, 0), "two_slot_native_auxv_terminator")
    for key, value in pairs[:-1]:
        _need(key != 0 and key not in values, "two_slot_native_auxv_duplicate")
        values[key] = value
    _need(all(values.get(key) == value for key, value in
              ((3, 0x400040), (4, 56), (5, 1), (6, 4096), (7, 0), (9, PROBE_ENTRY))),
          "two_slot_native_auxv_probe")


def qualify(backend=None):
    """Return a complete or diagnostic inline record without publishing it.

    Passing *any* backend explicitly selects the scripted evidence origin. This
    test seam cannot qualify a host; it never changes the native command's fixed
    probe, operation surface, observation deadline or cleanup deadline.
    """
    native_origin = backend is None
    backend = NativeBackend() if backend is None else backend
    started = backend.clock()
    deadline = started + OBSERVATION_NS
    probe = checker.probe_bytes()
    record = {
        "record_type": "required_gate_idempotence_loader_two_slot_qualification_v0",
        "profile": "linux_x86_64_loader_two_slot_qualification_v0",
        "evidence_origin": "native_owned_probe" if native_origin else "scripted_test_backend",
        "attempt_id": uuid.uuid4().hex, "status": "incomplete", "failure": None,
        "phase": "prepare", "context": None, "context_after": None,
        "sources": [], "sources_after": None,
        "process": {"observer_pid": backend.observer_pid, "child_pid": None,
                    "starttime": None, "pidfd": None, "proc_dir_pinned": False,
                    "unexpected_children": []},
        "probe": {**checker.binding(probe), "seals": None, "mode": None},
        "timing": {"started_ns": started, "cleanup_started_ns": None, "finished_ns": started},
        "operations": [], "raw": {}, "boundary": dict(checker.BOUNDARY),
    }
    total = 0
    sequence_complete = False
    failure = None
    initial_debug = struct.pack("<6Q", 0, 0, 0, 0, DR6_RESERVED, 0)
    armed_debug = struct.pack("<6Q", SLOT0_TARGET, SLOT1_TARGET, 0, 0, DR6_RESERVED, 5)

    def check_deadline():
        _need(backend.clock() < deadline, "two_slot_native_deadline")

    def update_snapshot():
        value = backend.snapshot()
        record["process"] = value["process"]
        record["probe"].update(value["probe"])

    def keep(name, data):
        nonlocal total
        maximum, _exact = checker.raw_limit(name)
        _need(type(data) is bytes and 0 < len(data) <= maximum, "two_slot_native_raw_limit")
        _need(name not in record["raw"] and len(record["raw"]) < 160
              and total + len(data) <= 262144, "two_slot_native_raw_budget")
        record["raw"][name] = {**checker.binding(data), "hex": data.hex()}
        total += len(data)
        return data

    def read(name):
        check_deadline()
        try:
            data = backend.read(name, deadline)
        except BaseException as exc:
            acquired = getattr(exc, "raw_bytes", None)
            if acquired is not None:
                keep(name, acquired)
            raise
        value = keep(name, data)
        check_deadline()
        return value

    def append(row):
        _need(len(record["operations"]) < 128, "two_slot_native_operation_budget")
        record["operations"].append(row)

    def call(row, function, *arguments):
        check_deadline()
        row.update({"at_ns": backend.clock(), "returncode": -1, "errno": 0})
        append(row)
        try:
            value = function(*arguments)
            _need(type(value) is int and value == 0, "two_slot_native_operation_return")
            row["returncode"] = value
            check_deadline()
        except BaseException as exc:
            row["errno"] = _error_number(exc)
            raise

    def wait(phase, expected):
        check_deadline()
        try:
            pid, status = backend.wait(deadline)
        except BaseException:
            observed = getattr(backend, "last_wait", None)
            if observed is not None:
                pid, status = observed
                if not any(row["op"] == "wait" and row["phase"] == phase
                           for row in record["operations"]):
                    append({"op": "wait", "at_ns": backend.clock(), "phase": phase,
                            "pid": pid, "status": status})
            raise
        append({"op": "wait", "at_ns": backend.clock(), "phase": phase,
                "pid": pid, "status": status})
        update_snapshot()
        if pid != record["process"]["child_pid"] or status != expected:
            # Capture only fixed, bounded read-only diagnostics. A stopped task
            # remains stopped; failure to read any diagnostic never resumes it.
            if os.WIFSTOPPED(status):
                names = ["unexpected.regs.bin", "unexpected.debug.bin", "unexpected.siginfo.bin"]
                if status >> 16 in (1, 2, 3):
                    names.insert(0, "unexpected.event_message.bin")
                for name in names:
                    try:
                        read(name)
                    except (OSError, ValueError):
                        pass
            raise QualificationError("two_slot_native_unexpected_wait")
        check_deadline()

    def write(number, value, phase):
        call({"op": "debug_write", "phase": phase, "register": number, "value": value},
             backend.write_debug, number, value)

    def resume(number, after):
        write(6, DR6_RESERVED, "resume.%02d" % number)
        _need(read("resume.%02d.debug.bin" % number) == (initial_debug if number == 0 else armed_debug),
              "two_slot_native_resume_debug_readback")
        call({"op": "continue", "after": after, "address": 0, "signal": 0}, backend.cont)

    try:
        record["context"] = backend.context()
        record["sources"] = backend.source_inventory()
        keep("probe.elf", probe)
        read("observer.stat.bin")
        read("observer.status.bin")
        record["phase"] = "spawn"
        backend.spawn(probe, deadline)
        update_snapshot()
        _need(record["probe"]["seals"] == 15 and record["probe"]["mode"] == 320,
              "two_slot_native_probe_seals")
        _need(read("probe.seals.bin") == struct.pack("<Q", 15)
              and read("probe.mode.bin") == struct.pack("<Q", 320), "two_slot_native_probe_seals")
        record["phase"] = "setup"
        wait("setup", 0x137F)
        read("child.stat.setup.bin")
        read("child.status.setup.bin")
        update_snapshot()
        _identity(record["raw"], "child.stat.setup.bin", "child.status.setup.bin", record["process"])
        read("child.pidfd.info.bin")
        _need(read("setup.debug.before.bin") == initial_debug, "two_slot_native_initial_debug")
        call({"op": "options", "value": PTRACE_OPTIONS}, backend.options)
        resume(0, "setup")
        record["phase"] = "exec"
        wait("exec", 0x4057F)
        record["phase"] = "cp0"
        read("cp0.child.stat.bin")
        read("cp0.child.status.bin")
        _identity(record["raw"], "cp0.child.stat.bin", "cp0.child.status.bin", record["process"])
        regs = read("cp0.regs.bin")
        _need(len(regs) == 216, "two_slot_native_register_size")
        words = struct.unpack("<27Q", regs)
        _need(words[16] == PROBE_ENTRY and words[18] & 0x100 == 0,
              "two_slot_native_cp0_registers")
        _auxv(read("cp0.auxv.bin"))
        _need(read("cp0.executable.elf") == probe, "two_slot_native_executable_identity")
        _need(read("cp0.debug.before.bin") == initial_debug, "two_slot_native_cp0_debug")
        record["phase"] = "arming"
        for number, value in ((0, SLOT0_TARGET), (1, SLOT1_TARGET), (6, DR6_RESERVED), (7, 5)):
            write(number, value, "arming")
        _need(read("cp0.debug.armed.bin") == armed_debug, "two_slot_native_arm_readback")
        resume(1, "cp0")
        for event in range(1, 11):
            phase = "event.%02d" % event
            record["phase"] = phase
            wait(phase, 0x57F)
            siginfo = read(phase + ".siginfo.bin")
            for side in ("a", "b"):
                for field in ("regs", "debug", "child.stat", "child.status", "code"):
                    read(phase + "." + field + "." + side + ".bin")
                append({"op": "sample", "at_ns": backend.clock(), "phase": phase, "side": side})
            raw = record["raw"]
            first = {field: bytes.fromhex(raw[phase + "." + field + ".a.bin"]["hex"])
                     for field in ("regs", "debug", "code")}
            for field, value in first.items():
                _need(value == bytes.fromhex(raw[phase + "." + field + ".b.bin"]["hex"]),
                      "two_slot_native_unstable_samples")
            _need(len(first["regs"]) == 216, "two_slot_native_register_size")
            words = struct.unpack("<27Q", first["regs"])
            target = words[16]
            _need(words[18] & 0x10000 != 0 and words[18] & 0x100 == 0,
                  "two_slot_native_resume_flags")
            _need(target in (SLOT0_TARGET, SLOT1_TARGET), "two_slot_native_event_target")
            expected_debug = struct.pack("<6Q", SLOT0_TARGET, SLOT1_TARGET, 0, 0,
                                        DR6_RESERVED | (1 if target == SLOT0_TARGET else 2), 5)
            _need(first["debug"] == expected_debug, "two_slot_native_event_debug")
            _need(first["code"] == probe[128:], "two_slot_native_probe_code_changed")
            for side in ("a", "b"):
                _identity(raw, phase + ".child.stat." + side + ".bin",
                          phase + ".child.status." + side + ".bin", record["process"])
            _need(len(siginfo) == 128 and struct.unpack_from("<iii", siginfo) == (5, 0, 4)
                  and struct.unpack_from("<Q", siginfo, 16)[0] == target,
                  "two_slot_native_siginfo")
            if event == 10 and target == SLOT0_TARGET:
                raise QualificationError("two_slot_native_unexpected_tenth_return")
            _need(target == (SLOT1_TARGET if event == 10 else SLOT0_TARGET)
                  and words[11] == (0 if event == 10 else 10 - event),
                  "two_slot_native_probe_progression")
            if event < 10:
                resume(event + 1, phase)
        sequence_complete = True
    except BaseException as exc:
        failure = _failure(exc)
    finally:
        try:
            update_snapshot()
        except BaseException as exc:
            failure = failure or _failure(exc)
        cleanup_started = backend.clock()
        record["timing"]["cleanup_started_ns"] = cleanup_started
        if failure is None:
            record["phase"] = "cleanup"
        try:
            rows = backend.cleanup(cleanup_started + CLEANUP_NS)
            for row in rows:
                append(row)
        except BaseException as exc:
            for row in getattr(backend, "cleanup_operations", []):
                if row not in record["operations"]:
                    try:
                        append(row)
                    except (OSError, ValueError):
                        break
            failure = failure or _failure(exc)
        try:
            update_snapshot()
            record["context_after"] = backend.context()
            record["sources_after"] = backend.source_inventory()
            _need(record["context_after"] == record["context"], "two_slot_native_context_changed")
            _need(record["sources_after"] == record["sources"], "two_slot_native_sources_changed")
        except BaseException as exc:
            failure = failure or _failure(exc)
        try:
            backend.close()
        except BaseException as exc:
            failure = failure or _failure(exc)
    finished = backend.clock()
    record["timing"]["finished_ns"] = finished
    if cleanup_started - started > OBSERVATION_NS or finished - cleanup_started > CLEANUP_NS:
        failure = failure or "two_slot_native_deadline"
    if not sequence_complete:
        failure = failure or "two_slot_native_incomplete_sequence"
    record["failure"] = failure
    if failure is None:
        record["status"], record["phase"] = "completed", "finished"
        try:
            encoded = checker.canonical(record)
            checker.verify_record(record_bytes=encoded,
                expected_record_sha256=hashlib.sha256(encoded).hexdigest(),
                expected_context=record["context"])
        except BaseException as exc:
            record["status"], record["failure"] = "incomplete", _failure(exc)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output = None
    try:
        # Reservation is the first side effect: an existing output cannot cause
        # even the fixed probe to execute, and is never replaced or truncated.
        output = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        before = os.fstat(output)
        _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
              "two_slot_native_output_identity")
        record = qualify()
        encoded = checker.canonical(record)
        _need(0 < len(encoded) <= 1024 * 1024, "two_slot_native_record_limit")
        current = os.stat(args.output, follow_symlinks=False)
        _need((current.st_dev, current.st_ino) == (before.st_dev, before.st_ino),
              "two_slot_native_output_replaced")
        remaining = memoryview(encoded)
        while remaining:
            count = os.write(output, remaining)
            _need(count > 0, "two_slot_native_output_write")
            remaining = remaining[count:]
        os.fsync(output)
        current = os.stat(args.output, follow_symlinks=False)
        _need((current.st_dev, current.st_ino) == (before.st_dev, before.st_ino),
              "two_slot_native_output_replaced")
        return 0 if record["status"] == "completed" else 2
    except BaseException as exc:
        # Invalidate only the inode this call exclusively created. A concurrent
        # replacement path belongs to someone else and is never unlinked or
        # truncated. A failed publication must not leave completed JSON in our
        # inode, even if the full write preceded an fsync/identity failure.
        if output is not None:
            try:
                os.ftruncate(output, 0)
            except OSError:
                pass
        sys.stderr.write(_failure(exc) + "\n")
        return 2
    finally:
        if output is not None:
            os.close(output)


if __name__ == "__main__":
    raise SystemExit(main())

