#!/usr/bin/env python3
"""Acquire one bounded suite for the authored containment task-guard probe.

Importing this module performs no native operation. Native execution requires
the explicit CLI acknowledgement and external probe/environment selections.
Any backend supplied by a caller is labelled scripted, even a NativeBackend.
The original startup helper, bubblewrap, static entry and runtime are never
launched here. This component does not qualify the full containment host.
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
import select
import signal
import stat
import struct
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_containment_task_guard_qualification_v0 as checker
import check_required_gate_idempotence_containment_task_guard_v0 as startup

ACKNOWLEDGEMENT = "QUALIFY_CONTAINMENT_TASK_GUARD_ONLY"
PTRACE_PEEKDATA, PTRACE_CONT, PTRACE_GETREGS, PTRACE_SYSCALL = 2, 7, 12, 24
PTRACE_GETEVENTMSG, PTRACE_GETSIGINFO, PTRACE_SEIZE = 0x4201, 0x4202, 0x4206
PTRACE_INTERRUPT, PTRACE_GET_SYSCALL_INFO = 0x4207, 0x420E
PTRACE_OPTIONS = 0x0010001F
WAIT_FLAGS = os.WNOHANG | 0x40000000  # __WALL, one global wait consumer.
READ_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
DIR_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_DIRECTORY
TOKEN = b"PULSEv0\n"
NS_NAMES = ("cgroup", "ipc", "mnt", "net", "pid", "pid_for_children",
            "time", "time_for_children", "user", "uts")
PROC_LIMIT = 65536
ELF_LIMIT = 262144
MAX_RECORD = 32 * 1024 * 1024
SUITE_NS, CASE_NS, CLEANUP_NS = 120_000_000_000, 5_000_000_000, 5_000_000_000
MARKER = 0x50554C5345515630


class QualificationError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class ObserverExitRequired(QualificationError):
    """A disposable native observer must publish this prefix and terminate."""
    def __init__(self, record):
        self.record = record
        super().__init__("task_guard_native_requires_observer_exit")


def need(condition, code):
    if not condition:
        raise QualificationError(code)


def failure_code(exc):
    code = getattr(exc, "code", None)
    if type(code) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", code):
        return code
    if isinstance(exc, OSError):
        return "task_guard_native_os_error_" + str(max(0, min(exc.errno or 0, 4095)))
    return "task_guard_native_interrupted" if not isinstance(exc, Exception) else "task_guard_native_failed"


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_uid, info.st_gid, info.st_mtime_ns, info.st_ctime_ns)


def read_regular(path, maximum):
    """Reuse the already reviewed no-follow ancestor and create-only I/O policy."""
    return startup._read_file(Path(path), maximum)


class ReservedOutput:
    """Reserve a new regular output before allowing any native acquisition."""
    def __init__(self, path):
        self.path = Path(path).absolute()
        self.dirs, self.fd, self.published = [], None, False
        self.before = None
        try:
            directory = os.open(self.path.anchor, DIR_FLAGS)
            self.dirs.append(directory)
            for component in self.path.parts[1:-1]:
                directory = os.open(component, DIR_FLAGS, dir_fd=directory)
                self.dirs.append(directory)
            self.fd = os.open(self.path.name, os.O_RDWR | os.O_CREAT | os.O_EXCL |
                              os.O_CLOEXEC | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            self.before = os.fstat(self.fd)
            need(stat.S_ISREG(self.before.st_mode) and self.before.st_nlink == 1,
                 "task_guard_native_output_identity")
        except BaseException:
            self.close()
            raise

    def _selected_name(self):
        current = os.stat(self.path.name, dir_fd=self.dirs[-1], follow_symlinks=False)
        need((current.st_dev, current.st_ino, current.st_mode, current.st_nlink) ==
             (self.before.st_dev, self.before.st_ino, self.before.st_mode, 1),
             "task_guard_native_output_replaced")
        return current

    def publish(self, raw):
        need(type(raw) is bytes and 0 < len(raw) <= MAX_RECORD and not self.published,
             "task_guard_native_output_extent")
        need(self._selected_name().st_size == 0 and os.fstat(self.fd).st_size == 0,
             "task_guard_native_output_modified")
        view = memoryview(raw)
        while view:
            count = os.write(self.fd, view)
            need(count > 0, "task_guard_native_output_short_write")
            view = view[count:]
        os.fsync(self.fd)
        need(self._selected_name().st_size == len(raw), "task_guard_native_output_size")
        os.lseek(self.fd, 0, os.SEEK_SET)
        checked = bytearray()
        while len(checked) <= len(raw):
            block = os.read(self.fd, min(65536, len(raw) + 1 - len(checked)))
            if not block:
                break
            checked.extend(block)
        need(bytes(checked) == raw, "task_guard_native_output_readback")
        # Rewalk the public path through the reviewed no-follow reader. A
        # renamed/replaced parent directory must not hide the reserved inode.
        need(read_regular(self.path, MAX_RECORD) == raw, "task_guard_native_output_path_changed")
        public = os.stat(self.path, follow_symlinks=False)
        need((public.st_dev, public.st_ino, public.st_mode, public.st_nlink) ==
             (self.before.st_dev, self.before.st_ino, self.before.st_mode, 1),
             "task_guard_native_output_public_identity")
        self._selected_name()
        self.published = True

    def close(self):
        try:
            if self.fd is not None and not self.published and self.before is not None:
                try:
                    self._selected_name()
                except (OSError, QualificationError):
                    pass
                else:
                    os.unlink(self.path.name, dir_fd=self.dirs[-1])
        finally:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None
            for descriptor in reversed(self.dirs):
                os.close(descriptor)
            self.dirs.clear()


class NativeBackend:
    """Read-only ptrace observations and owned pidfd control; no write requests.

    The only subject resumes are CONT to the first probe exec and SYSCALL
    afterwards. Every resume is authorized by the independent state machine.
    A failed pidfd acquisition never enables numeric-PID signalling.
    """

    def __init__(self):
        self.observer_pid = os.getpid()
        self.tasks = {}
        self.opened = set()
        self.barrier = None
        self.stdout = self.stderr = None
        self.original_subreaper = None
        self.libc = None
        self.emit = None
        self.deadline = None
        self.case_id = None
        self.probe = None
        self.sequence = 0
        self.last_wait_prefix = None
        self.last_wait_published = False

    def clock(self):
        return time.monotonic_ns()

    def _deadline(self, deadline=None):
        selected = self.deadline if deadline is None else deadline
        need(selected is None or self.clock() < selected, "task_guard_native_deadline")

    def _load_libc(self):
        if self.libc is None:
            self.libc = ctypes.CDLL(None, use_errno=True)
            self.libc.ptrace.argtypes = (ctypes.c_ulong, ctypes.c_ulong,
                                        ctypes.c_void_p, ctypes.c_void_p)
            self.libc.ptrace.restype = ctypes.c_long
            self.libc.prctl.argtypes = (ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                                       ctypes.c_ulong, ctypes.c_ulong)
            self.libc.prctl.restype = ctypes.c_int
            self.libc.syscall.restype = ctypes.c_long

    def _prctl(self, option, argument=0):
        self._load_libc()
        ctypes.set_errno(0)
        result = self.libc.prctl(option, argument, 0, 0, 0)
        if result == -1:
            raise OSError(ctypes.get_errno(), "prctl failed")
        need(result == 0, "task_guard_native_prctl_result")

    def _read_fd(self, descriptor, maximum, *, deadline=None):
        need(type(maximum) is int and 0 < maximum <= 64 * 1024 * 1024,
             "task_guard_native_read_bound")
        before = os.fstat(descriptor)
        need(stat.S_ISREG(before.st_mode), "task_guard_native_read_type")
        result = bytearray()
        try:
            while True:
                self._deadline(deadline)
                block = os.read(descriptor, min(65536, maximum + 1 - len(result)))
                if not block:
                    break
                result.extend(block)
                need(len(result) <= maximum, "task_guard_native_read_limit")
            need(_identity(os.fstat(descriptor)) == _identity(before),
                 "task_guard_native_read_changed")
            return bytes(result)
        except BaseException as exc:
            if result and len(result) <= maximum:
                exc.raw_bytes = bytes(result)
            raise

    def _read_path(self, path, maximum, *, directory=None, follow=False, deadline=None):
        descriptor = os.open(path, READ_FLAGS & ~os.O_NOFOLLOW if follow else READ_FLAGS,
                             dir_fd=directory)
        try:
            return self._read_fd(descriptor, maximum, deadline=deadline)
        finally:
            os.close(descriptor)

    def read_task(self, pid, field):
        # Exact field dispatch. In particular, status must never match stat.
        limits = {"stat": PROC_LIMIT, "status": PROC_LIMIT, "maps": PROC_LIMIT,
                  "cmdline": 4096, "environ": 4096, "exe": ELF_LIMIT}
        need(field in limits and pid in self.tasks, "task_guard_native_proc_field")
        task = self.tasks[pid]
        need(task["procfd"] is not None, "task_guard_native_proc_unpinned")
        return self._read_path(field, limits[field], directory=task["procfd"],
                               follow=field == "exe")

    def _status_fields(self, raw):
        fields = {}
        for row in raw.decode("ascii").splitlines():
            key, value = row.split(":", 1)
            need(key not in fields, "task_guard_native_status_duplicate")
            fields[key] = value.strip()
        return fields

    def context(self):
        need(sys.platform == "linux" and os.uname().machine == "x86_64"
             and sys.byteorder == "little" and ctypes.sizeof(ctypes.c_void_p) == 8
             and os.sysconf("SC_PAGE_SIZE") == 4096, "task_guard_native_platform")
        ids = {"uid": os.getuid(), "euid": os.geteuid(),
               "gid": os.getgid(), "egid": os.getegid()}
        need(ids["uid"] == ids["euid"] > 0 and ids["gid"] == ids["egid"] > 0,
             "task_guard_native_nonroot_ids")
        own = str(self.observer_pid)
        need(os.listdir("/proc/self/task") == [own], "task_guard_native_observer_threads")
        need(signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL,
             "task_guard_native_sigchld_handler")
        for descriptor in (0, 1, 2):
            os.fstat(descriptor)
        status_fields = self._status_fields(self._read_path("/proc/self/status", PROC_LIMIT))
        need(all(int(status_fields[name], 16) == 0 for name in ("CapEff", "CapPrm", "CapInh")),
             "task_guard_native_observer_capabilities")
        namespaces = {}
        for name in NS_NAMES:
            try:
                namespaces[name] = os.readlink("/proc/self/ns/" + name)
            except FileNotFoundError:
                need(name in ("time", "time_for_children"), "task_guard_native_namespace_missing")
                namespaces[name] = None
        uname = os.uname()
        return {
            "uname": {name: getattr(uname, name) for name in ("sysname", "release", "version", "machine")},
            "boot_id": self._read_path("/proc/sys/kernel/random/boot_id", 128).decode("ascii").strip(),
            "observer_executable": checker.binding(self._read_path("/proc/self/exe", 64 * 1024 * 1024, follow=True)),
            "python_version": list(sys.version_info[:3]), "ids": ids,
            "security": {name: int(status_fields[name]) if name in
                         ("NoNewPrivs", "Seccomp", "Seccomp_filters") else status_fields[name]
                         for name in ("NoNewPrivs", "Seccomp", "Seccomp_filters", "CapEff",
                                      "CapPrm", "CapInh", "CapBnd", "CapAmb")},
            "lsm_label_hex": self._read_path("/proc/self/attr/current", 4096).hex(),
            "namespaces": namespaces,
        }

    def prepare_observer(self):
        self._load_libc()
        need(not self._read_path("/proc/self/task/" + str(self.observer_pid) + "/children", 4096).strip(),
             "task_guard_native_observer_children")
        # Linux x86-64 glibc struct sigaction: handler, sigset_t, flags,
        # alignment and restorer. Read only; never replace caller disposition.
        class Sigaction(ctypes.Structure):
            _fields_ = [("handler", ctypes.c_void_p), ("mask", ctypes.c_ulong * 16),
                        ("flags", ctypes.c_int), ("restorer", ctypes.c_void_p)]
        need(ctypes.sizeof(Sigaction) == 152 and Sigaction.flags.offset == 136,
             "task_guard_native_sigaction_abi")
        action = Sigaction()
        self.libc.sigaction.argtypes = (ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
        self.libc.sigaction.restype = ctypes.c_int
        ctypes.set_errno(0)
        need(self.libc.sigaction(signal.SIGCHLD, None, ctypes.byref(action)) == 0
             and action.handler is None and action.flags & 2 == 0,
             "task_guard_native_sigchld_disposition")
        value = ctypes.c_int(-1)
        self._prctl(37, ctypes.addressof(value))
        need(value.value in (0, 1), "task_guard_native_subreaper_state")
        self.original_subreaper = value.value
        self._prctl(36, 1)
        self._prctl(37, ctypes.addressof(value))
        need(value.value == 1, "task_guard_native_subreaper_unconfirmed")
        return {"pid": self.observer_pid,
                "stat_hex": self._read_path("/proc/self/stat", PROC_LIMIT).hex(),
                "status_hex": self._read_path("/proc/self/status", PROC_LIMIT).hex(),
                "sigaction_hex": bytes(action).hex(),
                "subreaper_before": self.original_subreaper, "subreaper_after": value.value,
                "subreaper_restored": None}

    def restore_observer(self):
        if self.original_subreaper is not None:
            previous = self.original_subreaper
            self._prctl(36, previous)
            value = ctypes.c_int(-1)
            self._prctl(37, ctypes.addressof(value))
            need(value.value == self.original_subreaper, "task_guard_native_subreaper_restore")
            self.original_subreaper = None
            return previous
        return None

    def source_inventory(self):
        return checker.source_inventory()

    def _ptrace(self, request, pid, address=0, data=0):
        allowed = {PTRACE_PEEKDATA, PTRACE_CONT, PTRACE_GETREGS, PTRACE_SYSCALL,
                   PTRACE_GETEVENTMSG, PTRACE_GETSIGINFO, PTRACE_SEIZE,
                   PTRACE_INTERRUPT, PTRACE_GET_SYSCALL_INFO}
        need(request in allowed and pid in self.tasks and pid > 1,
             "task_guard_native_ptrace_request")
        need(type(address) is int and type(data) is int and address >= 0 and data >= 0,
             "task_guard_native_ptrace_arguments")
        if request in (PTRACE_CONT, PTRACE_INTERRUPT):
            need(address == data == 0, "task_guard_native_ptrace_control")
        elif request == PTRACE_SYSCALL:
            need(address == 0 and data in (0, signal.SIGCHLD)
                 and data == self.tasks[pid].get("signal", 0), "task_guard_native_ptrace_signal")
        elif request == PTRACE_SEIZE:
            need(address == 0 and data == PTRACE_OPTIONS, "task_guard_native_ptrace_options")
        elif request == PTRACE_PEEKDATA:
            need(data == 0 and address > 0, "task_guard_native_ptrace_peek")
        elif request == PTRACE_GET_SYSCALL_INFO:
            need(address == 88 and data > 0, "task_guard_native_ptrace_syscall_buffer")
        else:
            need(address == 0 and data > 0, "task_guard_native_ptrace_read_buffer")
        self._deadline()
        self._load_libc()
        ctypes.set_errno(0)
        result = self.libc.ptrace(request, pid, address, data)
        number = ctypes.get_errno()
        if result == -1 and number:
            raise OSError(number, "ptrace failed")
        if request == PTRACE_PEEKDATA:
            return result & ((1 << 64) - 1)
        if request == PTRACE_GET_SYSCALL_INFO:
            need(0 <= result <= 88, "task_guard_native_syscall_info_size")
        else:
            need(result == 0, "task_guard_native_ptrace_result")
        return result

    def _registers(self, pid):
        result = (ctypes.c_ubyte * 216)()
        self._ptrace(PTRACE_GETREGS, pid, data=ctypes.addressof(result))
        return bytes(result)

    def _syscall_info(self, pid):
        result = (ctypes.c_ubyte * 88)()
        size = self._ptrace(PTRACE_GET_SYSCALL_INFO, pid, 88, ctypes.addressof(result))
        return bytes(result)[:size]

    def _event_message(self, pid):
        result = ctypes.c_ulong(0)
        self._ptrace(PTRACE_GETEVENTMSG, pid, data=ctypes.addressof(result))
        return bytes(result)

    def _signal_info(self, pid):
        result = (ctypes.c_ubyte * 128)()
        self._ptrace(PTRACE_GETSIGINFO, pid, data=ctypes.addressof(result))
        return bytes(result)

    def read_memory(self, pid, address, length):
        need(type(address) is int and 0 < address < 1 << 63 and
             type(length) is int and 0 < length <= 65536 and address + length < 1 << 63,
             "task_guard_native_memory_range")
        result = bytearray()
        # Aligned PEEKDATA avoids reading a word beyond the selected final page.
        aligned = address & ~7
        try:
            while aligned < address + length:
                word = self._ptrace(PTRACE_PEEKDATA, pid, aligned).to_bytes(8, "little")
                left = max(address, aligned) - aligned
                right = min(address + length, aligned + 8) - aligned
                result.extend(word[left:right])
                aligned += 8
        except BaseException as exc:
            if result:
                exc.raw_bytes = bytes(result)
            raise
        return bytes(result)

    def _new_task(self, pid):
        if pid not in self.tasks:
            # One extra unexpected birth can be quarantined without resuming
            # either side. It is always incomplete, never a larger allowed graph.
            need(len(self.tasks) < 4, "task_guard_native_task_ledger_limit")
            self.tasks[pid] = {"pidfd": None, "procfd": None, "stopped": False,
                               "terminal": False, "execs": 0, "entry": None,
                               "order": len(self.tasks), "guard_memory": None,
                               "signal": 0}
        return self.tasks[pid]

    def _acquire(self, pid, operation):
        task = self._new_task(pid)
        need(task["pidfd"] is None, "task_guard_native_duplicate_pidfd")
        # Register the identity in the ledger BEFORE either fallible acquisition.
        task["pidfd"] = os.pidfd_open(pid, 0)
        self.opened.add(task["pidfd"])
        if task["procfd"] is None:
            task["procfd"] = os.open("/proc/" + str(pid), DIR_FLAGS)
            self.opened.add(task["procfd"])
        raw = {"stat": self.read_task(pid, "stat").hex(),
               "status": self.read_task(pid, "status").hex(),
               "pidfd_info": self._read_path("/proc/self/fdinfo/" + str(task["pidfd"]), 4096).hex()}
        self.emit({"op": operation, "pid": pid, "pidfd": task["pidfd"], "raw": raw})

    def _sealed(self, raw, mode):
        descriptor = os.memfd_create("pulse-containment-task-guard-v0", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        self.opened.add(descriptor)
        remaining = memoryview(raw)
        while remaining:
            self._deadline()
            count = os.write(descriptor, remaining)
            need(count > 0, "task_guard_native_memfd_write")
            remaining = remaining[count:]
        os.fchmod(descriptor, mode)
        fcntl.fcntl(descriptor, 1033, 15)
        need(fcntl.fcntl(descriptor, 1034) == 15, "task_guard_native_memfd_seals")
        readonly = os.open("/proc/self/fd/" + str(descriptor), os.O_RDONLY | os.O_CLOEXEC)
        self.opened.add(readonly)
        need(_identity(os.fstat(readonly)) == _identity(os.fstat(descriptor)),
             "task_guard_native_memfd_identity")
        need(self._read_fd(readonly, max(1, len(raw))) == raw, "task_guard_native_memfd_bytes")
        os.lseek(readonly, 0, os.SEEK_SET)
        os.close(descriptor)
        self.opened.remove(descriptor)
        return readonly

    def _bootstrap_child(self, inputs, case_name, observer_pid):
        """Owned Python bootstrap, outside the admitted probe interval.

        Its private bounded release pipe permits safe EOF self-exit even if
        parent pidfd acquisition fails. No selected native object is executed
        until the parent has consumed the initial SEIZE/INTERRUPT stop.
        """
        try:
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
            resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
            resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
            self._prctl(1, signal.SIGKILL)
            need(os.getppid() == observer_pid, "task_guard_native_bootstrap_parent")
            # Duplicate all five inputs before overwriting any target slot.
            copies = [fcntl.fcntl(descriptor, fcntl.F_DUPFD_CLOEXEC, 10) for descriptor in inputs]
            for target, descriptor in enumerate(copies):
                os.dup2(descriptor, target, inheritable=target != 4)
            ctypes.set_errno(0)
            need(self.libc.syscall(ctypes.c_long(436), ctypes.c_uint(5),
                                   ctypes.c_uint(0xFFFFFFFF), ctypes.c_uint(0)) == 0,
                 "task_guard_native_bootstrap_close_range")
            os.chdir("/")
            os.set_blocking(4, False)
            poller = select.poll()
            poller.register(4, select.POLLIN | select.POLLHUP)
            deadline = time.monotonic_ns() + CASE_NS
            data = bytearray()
            for _ in range(1024):
                need(time.monotonic_ns() < deadline and os.getppid() == observer_pid,
                     "task_guard_native_bootstrap_deadline")
                try:
                    block = os.read(4, len(TOKEN) + 1 - len(data))
                except BlockingIOError:
                    poller.poll(10)
                    continue
                if not block:
                    need(bytes(data) == TOKEN, "task_guard_native_bootstrap_token")
                    break
                data.extend(block)
                need(len(data) <= len(TOKEN) and TOKEN.startswith(data),
                     "task_guard_native_bootstrap_frame")
            else:
                raise QualificationError("task_guard_native_bootstrap_iterations")
            os.close(4)
            need(os.getppid() == observer_pid, "task_guard_native_bootstrap_parent_lost")
            os.execve(3, ["pulsemech-containment-task-probe-v0", case_name,
                          str(observer_pid), "initial"], {"LC_ALL": "C", "TZ": "UTC"})
        except BaseException:
            os._exit(120)
        os._exit(121)

    def begin_case(self, case_id, probe_bytes, emit, deadline):
        need(not self.tasks and not self.opened, "task_guard_native_case_reused")
        self.emit, self.deadline = emit, deadline
        self.case_id, self.probe = case_id, probe_bytes
        self._load_libc()
        empty = self._sealed(b"", 0o400)
        executable = self._sealed(probe_bytes, 0o500)
        out_r, out_w = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
        self.opened.update((out_r, out_w))
        self.stdout = out_r
        err_r, err_w = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
        self.opened.update((err_r, err_w))
        self.stderr = err_r
        gate_r, gate_w = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
        self.opened.update((gate_r, gate_w))
        self.barrier = gate_w
        need(all(fd > 2 for fd in self.opened), "task_guard_native_stdio_unavailable")
        self._deadline()
        child = os.fork()
        if child == 0:
            self._bootstrap_child((empty, out_w, err_w, executable, gate_r),
                                  checker.CASES[case_id - 1], self.observer_pid)
        self._new_task(child)
        for descriptor in (empty, executable, out_w, err_w, gate_r):
            os.close(descriptor)
            self.opened.remove(descriptor)
        self._acquire(child, "spawn")
        self._ptrace(PTRACE_SEIZE, child, data=PTRACE_OPTIONS)
        self.emit({"op": "seize", "pid": child, "options": PTRACE_OPTIONS})
        self._ptrace(PTRACE_INTERRUPT, child)
        self.emit({"op": "interrupt", "pid": child})
        return child

    def release(self, pid):
        need(self.barrier is not None and self.tasks[pid]["stopped"],
             "task_guard_native_release_state")
        self._deadline()
        need(os.write(self.barrier, TOKEN) == len(TOKEN), "task_guard_native_release_write")
        os.close(self.barrier)
        self.opened.remove(self.barrier)
        self.barrier = None
        self.emit({"op": "release", "pid": pid})

    def resume(self, pid, request):
        need(pid in self.tasks and self.tasks[pid]["stopped"] and request in ("cont", "syscall"),
             "task_guard_native_resume_state")
        pending_signal = self.tasks[pid].get("signal", 0)
        need(request == "syscall" or pending_signal == 0, "task_guard_native_bootstrap_signal")
        self._ptrace(PTRACE_CONT if request == "cont" else PTRACE_SYSCALL, pid, data=pending_signal)
        self.tasks[pid]["stopped"] = False
        self.tasks[pid]["signal"] = 0
        self.emit({"op": "resume", "pid": pid, "request": request, "signal": pending_signal})

    def _memory_for_stop(self, pid, info, raw, memory=None):
        memory = [] if memory is None else memory
        task = self.tasks[pid]
        def capture(address, length):
            try:
                data = self.read_memory(pid, address, length)
            except BaseException as exc:
                prefix = getattr(exc, "raw_bytes", None)
                if type(prefix) is bytes and 0 < len(prefix) <= length:
                    memory.append({"address": address, "hex": prefix.hex()})
                raise
            memory.append({"address": address, "hex": data.hex()})
            return data
        if len(info) >= 80 and info[0] == 1:
            number, *arguments = struct.unpack_from("<7Q", info, 24)
            task["entry"] = (number, arguments)
            if number == 157 and arguments[:2] == [22, 2]:
                fprog = capture(arguments[2], 16)
                count, pointer = struct.unpack_from("<H6xQ", fprog)
                need(count == 34, "task_guard_native_guard_length")
                program = capture(pointer, count * 8)
                task["guard_memory"] = [(arguments[2], fprog), (pointer, program)]
                raw["maps"] = self.read_task(pid, "maps").hex()
            elif number == 56 and arguments[0] == 0x01200011 and arguments[3] != 0:
                capture(arguments[3], 4)
                raw["maps"] = self.read_task(pid, "maps").hex()
            elif number == 39 and arguments[0] == MARKER and arguments[2] == 4:
                capture(arguments[4], 4)
                raw["maps"] = self.read_task(pid, "maps").hex()
            elif number == 322:
                capture(arguments[1], 1)
        elif len(info) >= 33 and info[0] == 2:
            previous = task["entry"]
            if previous is not None and previous[0] == 157 and previous[1][:2] == [22, 2]:
                for address, old in task["guard_memory"] or []:
                    capture(address, len(old))
                raw["maps"] = self.read_task(pid, "maps").hex()
            task["entry"] = None
        return memory

    def poll_wait(self, *, cleanup=False):
        self._deadline()
        self.last_wait_prefix = None
        self.last_wait_published = False
        try:
            pid, status = os.waitpid(-1, WAIT_FLAGS)
        except ChildProcessError:
            return "drained"
        if pid == 0:
            return None
        newly_seen = pid not in self.tasks
        task = self._new_task(pid)
        raw, memory = {}, []
        event = {"op": "wait", "pid": pid, "status": status, "raw": raw, "memory": memory}
        self.last_wait_prefix = event
        def read_field(field):
            try:
                data = self.read_task(pid, field)
            except BaseException as exc:
                prefix = getattr(exc, "raw_bytes", None)
                if type(prefix) is bytes and 0 < len(prefix) <= (ELF_LIMIT if field == "exe" else PROC_LIMIT):
                    raw[field] = prefix.hex()
                raise
            raw[field] = data.hex()
            return data
        if cleanup:
            # SIGKILL may have made a queued stop unreadable already. The raw
            # wait is still consumed, but cleanup never re-reads payload memory
            # or restarts a stopped task to obtain a tidier transcript.
            if os.WIFSTOPPED(status):
                task["stopped"] = True
            elif os.WIFEXITED(status) or os.WIFSIGNALED(status):
                task["terminal"] = True
                task["stopped"] = False
            else:
                raise QualificationError("task_guard_native_cleanup_wait_kind")
            self.last_wait_published = True
            self.emit(event)
            if newly_seen and task["pidfd"] is None and not task["terminal"]:
                self._acquire(pid, "acquire")
            return event
        if os.WIFSTOPPED(status):
            task["stopped"] = True
            ptrace_event = status >> 16
            if ptrace_event in (1, 4):
                raw["event_message"] = self._event_message(pid).hex()
            if ptrace_event == 1:
                # Account for a created child before any validation callback
                # can reject the parent's unexpected or malformed birth.
                child = int.from_bytes(bytes.fromhex(raw["event_message"]), "little")
                if child not in self.tasks:
                    self._new_task(child)
                    self._acquire(child, "acquire")
            if task["procfd"] is None:
                task["procfd"] = os.open("/proc/" + str(pid), DIR_FLAGS)
                self.opened.add(task["procfd"])
            # Establish observer-visible identity before reading tracee memory.
            read_field("stat")
            read_field("status")
            fields = self._status_fields(bytes.fromhex(raw["status"]))
            need(int(fields["TracerPid"]) == self.observer_pid,
                 "task_guard_native_wait_tracer")
            raw["regs"] = self._registers(pid).hex()
            if ptrace_event == 4:
                task["execs"] += 1
                read_field("exe")
                read_field("cmdline")
                read_field("environ")
            if os.WSTOPSIG(status) == signal.SIGTRAP | 0x80:
                info = self._syscall_info(pid)
                raw["syscall_info"] = info.hex()
                self._memory_for_stop(pid, info, raw, memory)
            elif ptrace_event == 0 and os.WSTOPSIG(status) == signal.SIGCHLD:
                raw["siginfo"] = self._signal_info(pid).hex()
                task["signal"] = signal.SIGCHLD
        elif os.WIFEXITED(status) or os.WIFSIGNALED(status):
            task["terminal"] = True
            task["stopped"] = False
        else:
            raise QualificationError("task_guard_native_wait_kind")
        self.last_wait_published = True
        self.emit(event)
        if newly_seen:
            self._acquire(pid, "acquire")
        return event

    def stopped(self):
        return [(pid, "cont" if task["execs"] == 0 and task["order"] == 0 else "syscall")
                for pid, task in self.tasks.items() if task["stopped"] and not task["terminal"]]

    def _close_barrier(self):
        if self.barrier is not None:
            os.close(self.barrier)
            self.opened.remove(self.barrier)
            self.barrier = None

    def cleanup(self, reason, emit, deadline):
        """One reverse signal pass, then globally drain; no terminal resumes."""
        self.deadline = deadline
        errors = []
        def error(code):
            if code not in errors and len(errors) < 16:
                errors.append(code)
        def safe_emit(event):
            try:
                emit(event)
            except BaseException as exc:
                # Logging/validation failure cannot cancel physical cleanup.
                error(failure_code(exc))
        self.emit = safe_emit
        try:
            self._close_barrier()
        except BaseException as exc:
            error(failure_code(exc))
        safe_emit({"op": "cleanup_begin", "reason": reason})
        signalled = set()
        def signal_new_tasks():
            for pid, task in sorted(self.tasks.items(), key=lambda item: item[1]["order"], reverse=True):
                if task["pidfd"] is None:
                    error("task_guard_native_cleanup_pidfd_missing")
                    continue
                if task["terminal"] or pid in signalled:
                    continue
                # Mark before the syscall, so an interrupted submission is not
                # retried. Newly discovered quarantined children get one pass.
                signalled.add(pid)
                result, number = 0, 0
                try:
                    self._deadline()
                    signal.pidfd_send_signal(task["pidfd"], signal.SIGKILL, None, 0)
                except OSError as exc:
                    result, number = -1, max(0, min(exc.errno or 0, 4095))
                    error(failure_code(exc))
                except BaseException as exc:
                    error(failure_code(exc))
                    result = -1
                safe_emit({"op": "pidfd_signal", "pid": pid, "pidfd": task["pidfd"],
                           "signal": signal.SIGKILL, "result": result, "errno": number})
        signal_new_tasks()
        hung_up = set()
        drained = False
        try:
            for _ in range(8192):
                self._deadline()
                try:
                    waited = self.poll_wait(cleanup=True)
                except BaseException as exc:
                    error(failure_code(exc))
                    waited = None
                signal_new_tasks()
                drained = waited == "drained"
                for pid, task in self.tasks.items():
                    if task["pidfd"] is None or pid in hung_up:
                        continue
                    poller = select.poll()
                    poller.register(task["pidfd"], select.POLLIN | select.POLLHUP | select.POLLERR)
                    ready = poller.poll(0)
                    revents = ready[0][1] if ready else 0
                    # Preserve changes/significant final evidence rather than
                    # emitting unbounded identical empty polls.
                    if revents != task.get("last_poll"):
                        safe_emit({"op": "pidfd_poll", "pid": pid, "pidfd": task["pidfd"], "revents": revents})
                        task["last_poll"] = revents
                    if revents & select.POLLHUP:
                        hung_up.add(pid)
                        task["hangup"] = True
                if drained and all(task["terminal"] for task in self.tasks.values()) and len(hung_up) == len(self.tasks):
                    safe_emit({"op": "wait_drained", "errno": errno.ECHILD})
                    break
                if waited is None or drained:
                    time.sleep(0.001)
            else:
                error("task_guard_native_cleanup_iteration_limit")
        except BaseException as exc:
            error(failure_code(exc))
        if not drained or len(hung_up) != len(self.tasks) or not all(t["terminal"] for t in self.tasks.values()):
            error("task_guard_native_cleanup_incomplete")
        return errors

    def unresolved_tasks(self):
        return [{"pid": pid, "pidfd": task["pidfd"], "terminal": task["terminal"],
                 "hangup": bool(task.get("hangup", False))}
                for pid, task in self.tasks.items() if not (task["terminal"] and task.get("hangup", False))]

    def finish_case(self):
        output = {}
        errors = []
        for name, descriptor in (("stdout_hex", self.stdout), ("stderr_hex", self.stderr)):
            data = bytearray()
            try:
                if descriptor is not None:
                    while True:
                        self._deadline()
                        chunk = os.read(descriptor, min(4096, 4097 - len(data)))
                        if not chunk:
                            break
                        data.extend(chunk)
                        need(len(data) <= 4096, "task_guard_native_output_limit")
            except BaseException as exc:
                errors.append(failure_code(exc))
            output[name] = bytes(data).hex()
        unresolved = {row["pid"] for row in self.unresolved_tasks()}
        retain = {fd for pid, task in self.tasks.items() if pid in unresolved
                  for fd in (task["pidfd"], task["procfd"]) if fd is not None}
        for descriptor in sorted(self.opened - retain, reverse=True):
            try:
                os.close(descriptor)
            except BaseException as exc:
                errors.append(failure_code(exc))
        self.opened.intersection_update(retain)
        self.tasks = {pid: task for pid, task in self.tasks.items() if pid in unresolved}
        self.barrier = self.stdout = self.stderr = None
        self.deadline = None
        if unresolved:
            errors.append("task_guard_native_requires_observer_exit")
        return output, errors


class Journal:
    def __init__(self, backend, state, events, suite_budget=None):
        self.backend, self.state, self.events = backend, state, events
        self.validating = True
        self.bytes = 0
        self.cleanup_mode = False
        self.suite_budget = suite_budget if suite_budget is not None else {"bytes": 0, "events": 0}

    def emit(self, event):
        if event.get("op") == "cleanup_begin":
            self.cleanup_mode = True
        row = {"seq": len(self.events), "t_ns": self.backend.clock(), **event}
        raw = checker.canonical(row)
        event_cap = 8192 if self.cleanup_mode else 8064
        byte_cap = MAX_RECORD - 2 * 1024 * 1024 - (0 if self.cleanup_mode else 65536)
        need(len(self.events) < event_cap and self.suite_budget["events"] < 65536
             and self.suite_budget["bytes"] + len(raw) + 1 <= byte_cap,
             "task_guard_native_journal_limit")
        self.events.append(row)
        self.bytes += len(raw)
        self.suite_budget["bytes"] += len(raw) + 1
        self.suite_budget["events"] += 1
        if self.validating:
            try:
                self.state.consume(row)
            except BaseException:
                self.validating = False
                raise


def collect_case(backend, case_id, probe_bytes, overall_deadline, suite_budget=None):
    start = backend.clock()
    row = {"case_id": case_id, "started_ns": start, "finished_ns": None,
           "failure": None, "cleanup_failures": [], "events": [],
           "stdout_hex": "", "stderr_hex": "", "unresolved_tasks": []}
    state = checker.TraceState(case_id, backend.observer_pid, probe_bytes)
    journal = Journal(backend, state, row["events"], suite_budget)
    released = False
    try:
        deadline = min(overall_deadline, start + CASE_NS)
        root = backend.begin_case(case_id, probe_bytes, journal.emit, deadline)
        for _ in range(8192):
            need(backend.clock() < deadline, "task_guard_native_case_deadline")
            if state.terminal_ready:
                break
            for pid, request in backend.stopped():
                if pid == root and not released:
                    backend.release(root)
                    released = True
                if state.can_resume(pid, request):
                    backend.resume(pid, request)
            observed = backend.poll_wait()
            need(observed != "drained" or state.terminal_ready,
                 "task_guard_native_early_wait_drain")
            if observed is None:
                time.sleep(0.001)
        else:
            raise QualificationError("task_guard_native_case_iteration_limit")
    except BaseException as exc:
        row["failure"] = failure_code(exc)
        journal.validating = False
        # A proc/memory read can fail after waitpid already consumed a stop.
        # Preserve the acquired raw prefix without calling it a valid stop.
        prefix = getattr(backend, "last_wait_prefix", None)
        if prefix is not None and not getattr(backend, "last_wait_published", False):
            try:
                journal.emit(prefix)
            except BaseException as preserve_error:
                row["cleanup_failures"].append(failure_code(preserve_error))
    finally:
        # Cleanup has a separate fixed budget; do not extend observation.
        cleanup_deadline = backend.clock() + CLEANUP_NS
        try:
            row["cleanup_failures"].extend(backend.cleanup(
                "failure" if row["failure"] else "normal", journal.emit, cleanup_deadline))
        except BaseException as exc:
            row["cleanup_failures"].append(failure_code(exc))
            journal.validating = False
        try:
            output, errors = backend.finish_case()
            row.update(output)
            row["cleanup_failures"].extend(errors)
            row["unresolved_tasks"] = backend.unresolved_tasks()
        except BaseException as exc:
            row["cleanup_failures"].append(failure_code(exc))
        row["finished_ns"] = backend.clock()
    if row["failure"] is None and not row["cleanup_failures"]:
        try:
            need(state.finished, "task_guard_native_record_not_finished")
            need(row["stdout_hex"] == row["stderr_hex"] == "", "task_guard_native_unexpected_output")
        except BaseException as exc:
            row["failure"] = failure_code(exc)
    return row


def qualify(*, probe_bytes, expected_probe_sha256, expected_environment_sha256,
            acknowledgement, backend=None):
    """Preserve one suite, stopping after the first incomplete case.

    Explicit backends are always scripted. This is intentionally decided here,
    not by a backend attribute or by a successful replay of authored events.
    """
    need(acknowledgement == ACKNOWLEDGEMENT, "task_guard_native_acknowledgement")
    need(type(probe_bytes) is bytes and 0 < len(probe_bytes) <= ELF_LIMIT,
         "task_guard_native_probe_size")
    need(hashlib.sha256(probe_bytes).hexdigest() == expected_probe_sha256,
         "task_guard_native_probe_digest")
    need(type(expected_environment_sha256) is str and
         re.fullmatch(r"[0-9a-f]{64}", expected_environment_sha256),
         "task_guard_native_environment_digest")
    origin = "native_owned_probe" if backend is None else "scripted_test_backend"
    backend = NativeBackend() if backend is None else backend
    started = backend.clock()
    result = {"record_type": checker.RECORD_TYPE, "profile": checker.PROFILE,
              "evidence_origin": origin, "attempt_id": uuid.uuid4().hex,
              "status": "incomplete", "failure": None, "cleanup_failures": [],
              "probe": {**checker.binding(probe_bytes), "hex": probe_bytes.hex()},
              "environment": None, "environment_after": None, "observer": None,
              "sources": [], "sources_after": [], "limits": dict(checker.LIMITS),
              "boundary": dict(checker.BOUNDARY),
              "timing": {"started_ns": started, "finished_ns": None}, "cases": []}
    suite_budget = {"bytes": 0, "events": 0}
    exit_required = False
    try:
        result["sources"] = backend.source_inventory()
        checker.verify_probe_elf(probe_bytes, expected_probe_sha256=expected_probe_sha256)
        checker.verify_prerequisite_source_contract()
        result["environment"] = backend.context()
        checker.validate_environment(result["environment"])
        need(checker.binding(checker.canonical(result["environment"]))["sha256"] == expected_environment_sha256,
             "task_guard_native_environment_selection")
        result["observer"] = backend.prepare_observer()
        overall_deadline = started + SUITE_NS
        for case_id in range(1, len(checker.CASES) + 1):
            need(backend.clock() < overall_deadline, "task_guard_native_suite_deadline")
            case = collect_case(backend, case_id, probe_bytes, overall_deadline, suite_budget)
            result["cases"].append(case)
            need(case["failure"] is None and not case["cleanup_failures"],
                 case["failure"] or "task_guard_native_case_cleanup_failed")
            need(len(checker.canonical(result)) <= MAX_RECORD, "task_guard_native_record_limit")
        result["environment_after"] = backend.context()
        result["sources_after"] = backend.source_inventory()
        need(checker.canonical(result["environment_after"]) == checker.canonical(result["environment"]),
             "task_guard_native_environment_changed")
        need(checker.canonical(result["sources_after"]) == checker.canonical(result["sources"]),
             "task_guard_native_sources_changed")
        result["status"] = "completed"
    except BaseException as exc:
        result["failure"] = failure_code(exc)
    finally:
        try:
            exit_required = bool(backend.unresolved_tasks())
            if exit_required:
                result["cleanup_failures"].append("task_guard_native_requires_observer_exit")
                result["status"] = "incomplete"
                if result["failure"] is None:
                    result["failure"] = "task_guard_native_cleanup_incomplete"
            else:
                restored = backend.restore_observer()
                if result["observer"] is not None:
                    result["observer"]["subreaper_restored"] = restored
        except BaseException as exc:
            result["cleanup_failures"].append(failure_code(exc))
            result["status"] = "incomplete"
            if result["failure"] is None:
                result["failure"] = failure_code(exc)
        result["timing"]["finished_ns"] = backend.clock()
    if result["status"] == "completed":
        try:
            raw = checker.canonical(result)
            checker.verify_record(record_bytes=raw,
                expected_record_sha256=checker.binding(raw)["sha256"],
                expected_probe_sha256=expected_probe_sha256,
                expected_environment_sha256=expected_environment_sha256)
        except BaseException as exc:
            result["status"] = "incomplete"
            result["failure"] = failure_code(exc)
    need(len(checker.canonical(result)) <= MAX_RECORD, "task_guard_native_final_record_limit")
    if exit_required and origin == "native_owned_probe":
        raise ObserverExitRequired(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", required=True, type=Path)
    parser.add_argument("--expected-probe-sha256", required=True)
    parser.add_argument("--expected-environment-sha256", required=True)
    parser.add_argument("--acknowledgement", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    need(args.acknowledgement == ACKNOWLEDGEMENT, "task_guard_native_acknowledgement")
    probe = read_regular(args.probe, ELF_LIMIT)
    destination = ReservedOutput(args.out)
    exit_required = False
    try:
        try:
            record = qualify(probe_bytes=probe,
                expected_probe_sha256=args.expected_probe_sha256,
                expected_environment_sha256=args.expected_environment_sha256,
                acknowledgement=args.acknowledgement)
        except ObserverExitRequired as exc:
            record, exit_required = exc.record, True
        destination.publish(checker.canonical(record))
    finally:
        try:
            destination.close()
        finally:
            if exit_required:
                # This CLI is the disposable observer. EXITKILL on its traced
                # tasks activates only when it actually exits. The saved prefix
                # explicitly retains missing removal proof; no success inferred.
                os._exit(1)
    return 0 if record["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
