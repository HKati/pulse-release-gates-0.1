#!/usr/bin/env python3
"""Acquire one acknowledged, bounded original-loader return/entry observation.

The production path reconstructs source/build and original-input admission,
then runs fresh fixed guard and two-slot capability probes in this observer.
Only after those checks may one owned original launcher run through nine
selected loader returns to its executable entry. The terminal entry is never
continued. Supplying any backend irrevocably selects scripted test evidence.
"""
from __future__ import annotations

import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_mapping_observation_v0 as proc
import check_required_gate_idempotence_entry_task_guard_v0 as guard_check
import check_required_gate_idempotence_loader_two_slot_qualification_v0 as probe_check
import qualify_required_gate_idempotence_loader_two_slot_v0 as probe
import required_gate_idempotence_entry_stop_v0 as entry
import required_gate_idempotence_entry_task_guard_v0 as guard
import required_gate_idempotence_loader_readout_v0 as readout
import required_gate_idempotence_loader_startup_readout_v0 as startup

ACKNOWLEDGEMENT = "OBSERVE_ORIGINAL_LOADER_NINE_RETURNS_AND_ENTRY_STOP_ONLY"
OBSERVATION_NS, CLEANUP_NS = 15_000_000_000, 2_000_000_000
DR6_RESERVED, DEBUGREG_OFFSET = 0xFFFF0FF0, 848
PTRACE_TRACEME, PTRACE_PEEKUSER, PTRACE_POKEUSER = 0, 3, 6
PTRACE_CONT, PTRACE_GETREGS = 7, 12
PTRACE_SETOPTIONS, PTRACE_GETEVENTMSG, PTRACE_GETSIGINFO = 0x4200, 0x4201, 0x4202
PTRACE_OPTIONS = 0x10001E
READ_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
DIRECTORY_FLAGS = READ_FLAGS | os.O_DIRECTORY
MAX_PROC, MAX_MEMORY = 65536, 16 * 1024 * 1024


class CollectionError(ValueError):
    """Stable failure without echoing raw process data or host paths."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise CollectionError(code)


def _failure(exc):
    if isinstance(exc, OSError):
        return "loader_resolution_os_error_" + str(exc.errno or 0)
    value = getattr(exc, "code", str(exc))
    return value if re.fullmatch(r"[a-z][a-z0-9_]{1,127}", value) else "loader_resolution_invalid"


def _binding(raw):
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def _file_identity(info):
    return {"dev": info.st_dev, "ino": info.st_ino, "size": info.st_size,
            "mode": info.st_mode, "nlink": info.st_nlink,
            "mtime_ns": info.st_mtime_ns, "ctime_ns": info.st_ctime_ns}


class NativeBackend(probe.NativeBackend):
    """Closed original-loader surface, reusing only bounded ownership helpers.

    The inherited context/read/wait/cleanup methods own the same process and
    descriptors throughout. The fixed probe's spawn, read dispatch and debug
    write policy are replaced here; its profile and public API are unchanged.
    """

    def __init__(self):
        super().__init__()
        self.native_files = None
        self.descriptors = {}
        self.process = None
        self.return_target = self.entry_target = None
        self.continuations = 0
        self.terminal_seen = False
        self.memfd = None
        self.initial_identities = None
        self.last_backings = []
        self.qualification_files = {}
        self.preload_root = self.preload_parent = None

    def _deadline(self, deadline):
        if deadline is not None:
            _need(self.clock() < deadline, "loader_resolution_deadline")

    def fresh_qualifications(self):
        """This call is below fresh admission and before any original fork."""
        self._platform()
        guard_raw = _canonical(guard.qualify())
        self.qualification_files["guard.qualification.json"] = guard_raw
        guard_check.validate_qualification(guard_raw, expected_sources=guard.source_bindings(),
                                          expected_environment=self.context())
        hardware_raw = _canonical(probe.qualify())
        self.qualification_files["two_slot.qualification.json"] = hardware_raw
        return guard_raw, hardware_raw

    def source_inventory(self):
        import required_gate_idempotence_loader_resolution_v0 as admission
        return admission.source_bindings()

    def snapshot(self):
        return {"observer_pid": self.observer_pid, "child_pid": self.child_pid,
                "starttime": self.starttime, "pidfd": self.pidfd,
                "proc_dir_pinned": self.procfd is not None,
                "unexpected_children": [dict(row) for row in self.unexpected_children]}

    def _ptrace(self, request, pid, address=0, data=0):
        allowed = {PTRACE_TRACEME, PTRACE_PEEKUSER, PTRACE_POKEUSER, PTRACE_CONT,
                   PTRACE_GETREGS, PTRACE_SETOPTIONS, PTRACE_GETEVENTMSG, PTRACE_GETSIGINFO}
        _need(type(request) is int and request in allowed,
              "loader_resolution_ptrace_request_forbidden")
        _need(type(pid) is int and type(address) is int and type(data) is int,
              "loader_resolution_ptrace_arguments")
        if request == PTRACE_TRACEME:
            _need(pid == address == data == 0, "loader_resolution_traceme_arguments")
        else:
            _need(pid == self.child_pid and pid is not None and pid > 0,
                  "loader_resolution_ptrace_owned_pid")
        if request == PTRACE_PEEKUSER:
            _need(address in {DEBUGREG_OFFSET + 8 * n for n in (0, 1, 2, 3, 6, 7)}
                  and data == 0, "loader_resolution_debug_read_forbidden")
        elif request == PTRACE_POKEUSER:
            choices = {DEBUGREG_OFFSET + 48: DR6_RESERVED}
            if self.return_target is not None and self.entry_target is not None:
                choices.update({DEBUGREG_OFFSET: self.return_target,
                                DEBUGREG_OFFSET + 8: self.entry_target,
                                DEBUGREG_OFFSET + 56: 5})
            _need(address in choices and data == choices[address],
                  "loader_resolution_debug_write_forbidden")
        elif request == PTRACE_SETOPTIONS:
            _need(address == 0 and data == PTRACE_OPTIONS,
                  "loader_resolution_options_forbidden")
        elif request == PTRACE_CONT:
            _need(address == data == 0 and not self.terminal_seen
                  and self.continuations < 11, "loader_resolution_continue_forbidden")
        elif request in (PTRACE_GETREGS, PTRACE_GETSIGINFO, PTRACE_GETEVENTMSG):
            _need(address == 0 and data > 0, "loader_resolution_read_buffer")
        ctypes.set_errno(0)
        result = self.libc.ptrace(request, pid, address, data)
        number = ctypes.get_errno()
        if result == -1 and number:
            raise OSError(number, "ptrace operation failed")
        if request == PTRACE_PEEKUSER:
            return result & ((1 << 64) - 1)
        _need(result == 0, "loader_resolution_ptrace_return")
        if request == PTRACE_CONT:
            self.continuations += 1
        return result

    def prepare(self, native_files, deadline):
        self._platform()
        self._deadline(deadline)
        _need(type(native_files) is dict and set(native_files) == set(readout.NATIVE_BINDINGS),
              "loader_resolution_native_roster")
        for path, expected in readout.NATIVE_BINDINGS.items():
            _need(type(native_files[path]) is bytes and _binding(native_files[path]) == expected,
                  "loader_resolution_native_binding")
        self.native_files = native_files
        self.descriptors[readout.LAUNCHER] = entry._sealed_launcher(native_files[readout.LAUNCHER])
        for path in sorted(native_files):
            if path == readout.LAUNCHER:
                continue
            host = ("/lib64/ld-linux-x86-64.so.2" if path == readout.LOADER else
                    "/usr/lib/x86_64-linux-gnu/" + Path(path).name)
            self._deadline(deadline)
            self.descriptors[path] = entry._open_native(host)
        self.initial_identities = {path: _file_identity(os.fstat(fd))
                                   for path, fd in self.descriptors.items()}

    def acquire_backings(self, deadline):
        """Re-read every pinned FD; deduplication occurs only after acquisition."""
        self._deadline(deadline)
        _need(self.native_files is not None and set(self.descriptors) == set(self.native_files),
              "loader_resolution_native_descriptors")
        result = self.last_backings = []
        for path in sorted(self.descriptors):
            fd = self.descriptors[path]
            before = _file_identity(os.fstat(fd))
            _need(stat.S_ISREG(before["mode"]) and not before["mode"] & 0o6000,
                  "loader_resolution_backing_kind")
            os.lseek(fd, 0, os.SEEK_SET)
            raw = self._read_fd(fd, readout.NATIVE_BINDINGS[path]["size_bytes"], deadline)
            after = _file_identity(os.fstat(fd))
            _need(before == after == self.initial_identities[path]
                  and raw == self.native_files[path], "loader_resolution_backing_changed")
            if path == readout.LAUNCHER:
                _need(fcntl.fcntl(fd, fcntl.F_GET_SEALS) == 15
                      and stat.S_IMODE(before["mode"]) == 0o500,
                      "loader_resolution_launcher_seals")
            result.append({"native_path": path, "before": before, "after": after,
                           "content": {"path": "native." + _binding(raw)["sha256"] + ".elf",
                                       **_binding(raw)}})
        return result

    def spawn(self, attempt_id, request_sha256, deadline):
        self._platform()
        self._deadline(deadline)
        _need(self.child_pid is None and self.native_files is not None,
              "loader_resolution_spawn_once")
        self.process = entry._spawn_child(self.descriptors[readout.LAUNCHER],
                                         self.observer_pid, attempt_id, request_sha256)
        self.child_pid = self.process.pid
        # Ownership precedes either fallible descriptor open.
        self.pidfd = os.pidfd_open(self.child_pid, 0)
        self.procfd = os.open("/proc/" + str(self.child_pid), DIRECTORY_FLAGS)
        return self.snapshot()

    def read_proc(self, role, deadline):
        """Exact roles avoid the previous child.stat/child.status overlap."""
        self._deadline(deadline)
        _need(role in {"observer.stat", "observer.status", "observer.exe", "boot_id",
                       "child.stat", "child.status",
                       "maps", "auxv", "pidfd.info", "cwd", "fds", "guard.receipt",
                       "executable", "exe.link"}, "loader_resolution_proc_role")
        if role in ("observer.stat", "observer.status"):
            return self._read_path(role.split(".")[1], MAX_PROC, deadline,
                                   directory=self.observerfd)
        if role == "observer.exe":
            return self._read_path("exe", 64 * 1024 * 1024, deadline,
                                   follow=True, directory=self.observerfd)
        if role == "boot_id":
            return self._read_path("/proc/sys/kernel/random/boot_id", 128, deadline)
        if role in ("child.stat", "child.status", "maps", "auxv"):
            name = role.split(".")[-1]
            raw = self._read_path(name, 1024 if name == "auxv" else MAX_PROC, deadline,
                                  directory=self.procfd)
            if role == "child.stat" and self.starttime is None:
                self.starttime = proc.parse_proc_stat(raw)["starttime"]
            return raw
        if role == "pidfd.info":
            return self._read_path("/proc/self/fdinfo/" + str(self.pidfd), MAX_PROC, deadline)
        if role == "cwd":
            return os.readlink("cwd", dir_fd=self.procfd).encode("utf-8")
        if role == "fds":
            return _canonical(guard.descriptor_snapshot(self.child_pid))
        if role == "guard.receipt":
            return entry._read_guard_receipt(self.process)
        if role == "exe.link":
            return os.readlink("exe", dir_fd=self.procfd).encode("utf-8")
        # Follow the fixed procfs executable magic link, not a claimed name.
        raw = self._read_path("exe", readout.NATIVE_BINDINGS[readout.LAUNCHER]["size_bytes"],
                              deadline, follow=True, directory=self.procfd)
        descriptor, other = entry.prior._read_executable(self.procfd, deadline)
        retained = os.fstat(self.descriptors[readout.LAUNCHER])
        _need(raw == other == self.native_files[readout.LAUNCHER]
              and descriptor["stat"]["dev"] == retained.st_dev
              and descriptor["stat"]["ino"] == retained.st_ino
              and descriptor["seals"] == 15, "loader_resolution_executable_backing")
        return raw

    def executable(self, deadline):
        self._deadline(deadline)
        fd = os.open("exe", os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK,
                     dir_fd=self.procfd)
        try:
            before = _file_identity(os.fstat(fd))
            seals_before = fcntl.fcntl(fd, fcntl.F_GET_SEALS)
            raw = self._read_fd(fd, readout.NATIVE_BINDINGS[readout.LAUNCHER]["size_bytes"], deadline)
            after = _file_identity(os.fstat(fd))
            _need(before == after == self.initial_identities[readout.LAUNCHER]
                  and seals_before == fcntl.fcntl(fd, fcntl.F_GET_SEALS) == 15
                  and raw == self.native_files[readout.LAUNCHER],
                  "loader_resolution_executable_backing")
            return ({"native_path": readout.LAUNCHER, "before": before, "after": after,
                     "content": {"path": "native." + _binding(raw)["sha256"] + ".elf",
                                 **_binding(raw)}}, raw)
        finally:
            os.close(fd)

    def environment(self, deadline):
        self._deadline(deadline)
        preload = self.preload(deadline, child=True)
        cwd = os.readlink("cwd", dir_fd=self.procfd).encode("utf-8")
        _need(0 < len(cwd) <= 4096, "loader_resolution_cwd_extent")
        namespaces = {}
        for name in probe.NAMESPACE_NAMES:
            self._deadline(deadline)
            try:
                namespaces[name] = os.readlink("ns/" + name, dir_fd=self.procfd)
            except FileNotFoundError:
                if name not in ("time", "time_for_children"):
                    raise
                namespaces[name] = None
        self._deadline(deadline)
        return _canonical({"cwd_hex": cwd.hex(), "namespaces": namespaces, "preload": preload})

    def preload(self, deadline, *, child=False):
        """Inspect only the fixed loader preload file through a pinned root.

        The owned task's procfs root magic link is deliberately followed; its
        directory identity must match the prelaunch root. The ``etc`` directory
        and final basename are opened without following symlinks. ENOENT is
        accepted only for that basename in the already pinned directory.
        """
        self._deadline(deadline)
        rootfd = parentfd = filefd = None
        try:
            if child:
                _need(self.procfd is not None and self.preload_root is not None,
                      "loader_resolution_preload_child_root_unbound")
                rootfd = os.open("root", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC |
                                 os.O_NONBLOCK, dir_fd=self.procfd)
            else:
                rootfd = os.open("/", DIRECTORY_FLAGS)
            root_before = _file_identity(os.fstat(rootfd))
            _need(stat.S_ISDIR(root_before["mode"]), "loader_resolution_preload_root_kind")
            parentfd = os.open("etc", DIRECTORY_FLAGS, dir_fd=rootfd)
            parent_before = _file_identity(os.fstat(parentfd))
            _need(stat.S_ISDIR(parent_before["mode"]), "loader_resolution_preload_parent_kind")
            for actual, selected in ((root_before, self.preload_root),
                                     (parent_before, self.preload_parent)):
                if selected is not None:
                    _need(all(actual[key] == selected[key] for key in ("dev", "ino", "mode")),
                          "loader_resolution_preload_root_changed")
            self._deadline(deadline)
            try:
                named_before = _file_identity(os.stat("ld.so.preload", dir_fd=parentfd,
                                                      follow_symlinks=False))
            except FileNotFoundError as exc:
                _need(exc.errno == 2, "loader_resolution_preload_absence_errno")
                named_before = None
            if named_before is None:
                try:
                    filefd = os.open("ld.so.preload", READ_FLAGS, dir_fd=parentfd)
                except FileNotFoundError as exc:
                    _need(exc.errno == 2, "loader_resolution_preload_absence_errno")
                else:
                    raise CollectionError("loader_resolution_preload_appeared_during_read")
                self._deadline(deadline)
                try:
                    os.stat("ld.so.preload", dir_fd=parentfd, follow_symlinks=False)
                except FileNotFoundError as exc:
                    _need(exc.errno == 2, "loader_resolution_preload_absence_errno")
                else:
                    raise CollectionError("loader_resolution_preload_appeared_during_read")
                state, file_record, open_errno = "absent", None, 2
            else:
                _need(stat.S_ISREG(named_before["mode"]) and named_before["size"] == 0,
                      "loader_resolution_preload_not_empty_regular")
                filefd = os.open("ld.so.preload", READ_FLAGS, dir_fd=parentfd)
                before = _file_identity(os.fstat(filefd))
                _need(before == named_before, "loader_resolution_preload_replaced")
                self._deadline(deadline)
                raw = os.read(filefd, 1)
                self._deadline(deadline)
                after = _file_identity(os.fstat(filefd))
                named_after = _file_identity(os.stat("ld.so.preload", dir_fd=parentfd,
                                                     follow_symlinks=False))
                _need(raw == b"" and before == after == named_after,
                      "loader_resolution_preload_changed_during_read")
                state, file_record, open_errno = "empty", {"before": before, "after": after}, 0
            parent_after = _file_identity(os.fstat(parentfd))
            root_after = _file_identity(os.fstat(rootfd))
            _need(parent_before == parent_after and root_before == root_after,
                  "loader_resolution_preload_directory_changed")
            self._deadline(deadline)
            if not child:
                self.preload_root, self.preload_parent = root_before, parent_before
            return {"status": state, "root": {"before": root_before, "after": root_after},
                    "parent": {"before": parent_before, "after": parent_after},
                    "file": file_record, "content": _binding(b""), "open_errno": open_errno}
        finally:
            close_failure = None
            for fd in (filefd, parentfd, rootfd):
                if fd is not None:
                    try:
                        os.close(fd)
                    except BaseException as exc:
                        close_failure = close_failure or exc
            if close_failure is not None:
                raise close_failure

    def registers(self, deadline):
        self._deadline(deadline)
        words = (ctypes.c_uint64 * 27)()
        self._ptrace(PTRACE_GETREGS, self.child_pid, 0, ctypes.addressof(words))
        return bytes(words)

    def debug_registers(self, deadline):
        self._deadline(deadline)
        return struct.pack("<6Q", *(self._ptrace(PTRACE_PEEKUSER, self.child_pid,
            DEBUGREG_OFFSET + 8 * number) for number in (0, 1, 2, 3, 6, 7)))

    def siginfo(self, deadline):
        self._deadline(deadline)
        words = (ctypes.c_uint64 * 16)()
        self._ptrace(PTRACE_GETSIGINFO, self.child_pid, 0, ctypes.addressof(words))
        return bytes(words)

    def event_message(self, deadline):
        self._deadline(deadline)
        value = ctypes.c_ulong()
        self._ptrace(PTRACE_GETEVENTMSG, self.child_pid, 0, ctypes.addressof(value))
        return struct.pack("<Q", value.value)

    def memory(self, address, size, deadline):
        raw = None
        try:
            self._deadline(deadline)
            _need(type(address) is int and type(size) is int and 0 < address < (1 << 47)
                  and 0 < size <= MAX_MEMORY and address + size < (1 << 47),
                  "loader_resolution_memory_extent")
            if self.memfd is None:
                self.memfd = os.open("mem", READ_FLAGS, dir_fd=self.procfd)
            before = os.fstat(self.memfd)
            _need(stat.S_ISREG(before.st_mode) and before.st_size == 0 and before.st_nlink == 1
                  and not before.st_mode & 0o111, "loader_resolution_memory_object")
            raw = os.pread(self.memfd, size, address)
            after = os.fstat(self.memfd)
            _need((before.st_dev, before.st_ino, before.st_mode, before.st_size) ==
                  (after.st_dev, after.st_ino, after.st_mode, after.st_size),
                  "loader_resolution_memory_identity")
            _need(len(raw) == size, "loader_resolution_memory_short_read")
            self._deadline(deadline)
            return raw
        except BaseException as exc:
            if type(raw) is bytes and type(size) is int and 0 < len(raw) <= size <= MAX_MEMORY:
                # A late deadline or changed descriptor is still a failed read;
                # retain its bounded bytes without converting it to success.
                exc.raw_bytes = raw
            raise

    def set_targets(self, return_target, entry_target):
        _need(self.return_target is None and self.entry_target is None
              and type(return_target) is int and type(entry_target) is int
              and 0 < return_target < (1 << 47) and 0 < entry_target < (1 << 47)
              and return_target != entry_target, "loader_resolution_target_selection")
        self.return_target, self.entry_target = return_target, entry_target

    def guard_metadata(self):
        if self.process is None:
            return {"launcher_fd": None, "receipt_fd": None}
        return {"launcher_fd": self.process.launcher_fd,
                "receipt_fd": self.process.receipt_fd}

    def options(self):
        return self._ptrace(PTRACE_SETOPTIONS, self.child_pid, 0, PTRACE_OPTIONS)

    def write_debug(self, number, value):
        _need(type(number) is int and number in (0, 1, 6, 7),
              "loader_resolution_debug_write_forbidden")
        return self._ptrace(PTRACE_POKEUSER, self.child_pid,
                            DEBUGREG_OFFSET + 8 * number, value)

    def cont(self):
        return self._ptrace(PTRACE_CONT, self.child_pid)

    def mark_terminal(self):
        self.terminal_seen = True

    def stable_stop(self, deadline):
        self._deadline(deadline)
        pid, status = os.waitpid(self.child_pid, os.WNOHANG | os.WUNTRACED | os.WCONTINUED)
        if pid:
            self.last_wait = (pid, status)
            if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                self.reaped = True
            raise CollectionError("loader_resolution_checkpoint_wait_changed")

    def drain_outputs(self, deadline):
        result = {}
        if self.process is None:
            return result
        try:
            for name in ("stdout", "stderr"):
                stream = getattr(self.process, name)
                os.set_blocking(stream.fileno(), False)
                raw = bytearray()
                try:
                    while True:
                        self._deadline(deadline)
                        try:
                            block = os.read(stream.fileno(), min(4096, 4097 - len(raw)))
                        except BlockingIOError as exc:
                            raise CollectionError("loader_resolution_output_not_closed") from exc
                        if not block:
                            break
                        raw.extend(block)
                        _need(len(raw) <= 4096, "loader_resolution_output_limit")
                finally:
                    result[name + ".bin"] = bytes(raw[:4096])
        except BaseException as exc:
            exc.output_files = result
            raise
        return result

    def close(self):
        failure = None
        for fd in [self.memfd, *self.descriptors.values()]:
            if fd is not None:
                try:
                    os.close(fd)
                except BaseException as exc:
                    failure = failure or exc
        if self.process is not None:
            for name in ("stdout", "stderr", "guard_receipt"):
                try:
                    getattr(self.process, name).close()
                except BaseException as exc:
                    failure = failure or exc
        try:
            super().close()
        except BaseException as exc:
            failure = failure or exc
        if failure is not None:
            raise failure


def collect(*, request_bytes, expected_request_sha256, accepted_policy_sha256,
            acknowledgement, admission_inputs=None, backend=None):
    """Return bounded raw evidence after fresh admission and owned cleanup.

    The acknowledgement covers the fixed fresh capability probes followed by
    one original-loader attempt. The external policy digest is selected by the
    caller; neither a request field nor a saved report can select it. Any
    explicitly supplied backend produces only scripted_test_backend evidence.
    No native work is performed on an invalid acknowledgement or admission.
    """
    import required_gate_idempotence_loader_resolution_v0 as admission
    import required_gate_idempotence_loader_resolution_readout_v0 as decoding

    _need(acknowledgement == ACKNOWLEDGEMENT,
          "loader_resolution_owner_acknowledgement_required")
    admitted = admission.reconstruct_admission(request_bytes=request_bytes,
        expected_request_sha256=expected_request_sha256,
        admission_inputs=admission_inputs, accepted_policy_sha256=accepted_policy_sha256)
    request, native, static_record = (admitted["request"], admitted["native_files"],
                                      admitted["static_record"])
    native_origin = backend is None
    backend = NativeBackend() if native_origin else backend
    files, total = {}, 0
    now = backend.clock()
    capture = {
        "record_type": "required_gate_idempotence_loader_resolution_capture_v0",
        "profile": admission.PROFILE,
        "evidence_origin": "native_original_loader_capture" if native_origin else "scripted_test_backend",
        "attempt_id": request["attempt_id"], "request_sha256": expected_request_sha256,
        "status": "incomplete", "failure": None, "context": None,
        "process": {"observer_pid": backend.observer_pid, "child_pid": None,
                    "starttime": None, "pidfd": None, "proc_dir_pinned": False,
                    "unexpected_children": []},
        "timing": {"started_ns": now, "cleanup_started_ns": None, "finished_ns": now},
        "guard": {"launcher_fd": None, "receipt_fd": None},
        "operations": [], "cp0": None, "returns": [], "entry": None,
        "files": {}, "boundary": dict(admission.BOUNDARY),
    }
    limits = admission.LIMITS
    deadline = None
    failure, complete = None, False
    qualified_observer = None
    guard_record = hardware_record = None
    initial_debug = struct.pack("<6Q", 0, 0, 0, 0, DR6_RESERVED, 0)
    armed_debug = None
    backing_identities = None
    preload_before = None

    def keep(name, raw, maximum=None):
        nonlocal total
        _need(type(name) is str and re.fullmatch(r"[a-z0-9_.-]{1,160}", name)
              and type(raw) is bytes, "loader_resolution_raw_name")
        maximum = limits["max_raw_bytes"] if maximum is None else maximum
        _need(len(raw) <= maximum, "loader_resolution_raw_extent")
        if name in files:
            _need(files[name] == raw, "loader_resolution_raw_replacement")
        else:
            # Reserve the final capture member and its bounded control bytes;
            # an acquisition prefix must remain publishable after any failure.
            _need(len(files) < limits["max_raw_files"] - 1
                  and total + len(raw) <= limits["max_raw_bytes"] - limits["max_control_bytes"],
                  "loader_resolution_raw_budget")
            files[name] = raw
            total += len(raw)
            capture["files"][name] = _binding(raw)
        return {"path": name, **_binding(raw)}

    def append(row):
        _need(len(capture["operations"]) < limits["max_operations"],
              "loader_resolution_operation_budget")
        capture["operations"].append(row)

    def check_time():
        _need(deadline is None or backend.clock() < deadline, "loader_resolution_deadline")

    def read_keep(name, function, *arguments, maximum=MAX_PROC):
        check_time()
        try:
            raw = function(*arguments)
        except BaseException as exc:
            prefix = getattr(exc, "raw_bytes", None)
            if type(prefix) is bytes and prefix:
                keep(name, prefix, maximum)
            raise
        descriptor = keep(name, raw, maximum)
        check_time()
        return descriptor

    def update_process():
        capture["process"] = backend.snapshot()
        capture["guard"] = backend.guard_metadata()

    def call(row, function, *arguments):
        check_time()
        row.update({"at_ns": backend.clock(), "returncode": -1, "errno": 0})
        append(row)
        try:
            value = function(*arguments)
            _need(type(value) is int and value == 0, "loader_resolution_operation_return")
            row["returncode"] = value
            check_time()
        except BaseException as exc:
            row["errno"] = int(getattr(exc, "errno", 0) or 0)
            raise

    def write(number, value, phase):
        call({"op": "debug_write", "phase": phase, "register": number, "value": value},
             backend.write_debug, number, value)

    def resume(number, after):
        write(6, DR6_RESERVED, "resume.%02d" % number)
        name = "resume.%02d.debug.bin" % number
        read_keep(name, backend.debug_registers, deadline, maximum=48)
        _need(files[name] == (initial_debug if number == 0 else armed_debug),
              "loader_resolution_resume_debug_readback")
        call({"op": "continue", "after": after, "address": 0, "signal": 0}, backend.cont)

    def wait(phase, expected):
        check_time()
        try:
            pid, status = backend.wait(deadline)
        except BaseException:
            observed = getattr(backend, "last_wait", None)
            if observed is not None:
                pid, status = observed
                append({"op": "wait", "at_ns": backend.clock(), "phase": phase,
                        "pid": pid, "status": status})
            raise
        append({"op": "wait", "at_ns": backend.clock(), "phase": phase,
                "pid": pid, "status": status})
        update_process()
        if pid != capture["process"]["child_pid"] or status != expected:
            if os.WIFSTOPPED(status):
                for name, function, maximum in (
                    ("unexpected.regs.bin", backend.registers, 216),
                    ("unexpected.debug.bin", backend.debug_registers, 48),
                    ("unexpected.siginfo.bin", backend.siginfo, 128),
                ):
                    try:
                        read_keep(name, function, deadline, maximum=maximum)
                    except (OSError, ValueError):
                        pass
            raise CollectionError("loader_resolution_unexpected_wait")
        check_time()

    def identity(stat_raw, status_raw):
        process = capture["process"]
        comm = probe._stat_identity(stat_raw, process)
        probe._status_identity(status_raw, process, comm)

    def point(phase, sample_started_ns=None):
        value = {"phase": phase, "sample_started_ns": (backend.clock() if sample_started_ns is None
                                                        else sample_started_ns),
                 "sample_finished_ns": None, "raw_files": {}, "backings": [],
                 "runtime_ranges": [], "loader_rx_range": None,
                 "native_rx_ranges": [], "executable": None}
        if phase == "cp0":
            capture["cp0"] = value
        elif phase == "entry":
            capture["entry"] = value
        else:
            _need(len(capture["returns"]) < 10, "loader_resolution_return_budget")
            capture["returns"].append(value)
        return value

    def checkpoint_read(checkpoint, role, function, *arguments, maximum=MAX_PROC):
        path = checkpoint["phase"] + "." + role
        try:
            descriptor = read_keep(path, function, *arguments, maximum=maximum)
        except BaseException:
            if path in files:
                checkpoint["raw_files"][role] = {"path": path, **_binding(files[path])}
            raise
        checkpoint["raw_files"][role] = descriptor
        return files[descriptor["path"]]

    def checkpoint_raw(checkpoint, role):
        return files[checkpoint["raw_files"][role]["path"]]

    def shared_roles(checkpoint):
        for name in ("observer.stat.bin", "observer.status.bin", "child.stat.setup.bin",
                     "child.status.setup.bin", "child.pidfd.info.bin"):
            checkpoint["raw_files"][name] = {"path": name, **_binding(files[name])}

    def sample_state(checkpoint, side):
        for kind in ("child.stat", "child.status", "maps", "auxv"):
            checkpoint_read(checkpoint, kind + "." + side + ".bin",
                            backend.read_proc, kind, deadline,
                            maximum=1024 if kind == "auxv" else MAX_PROC)
        update_process()
        identity(checkpoint_raw(checkpoint, "child.stat." + side + ".bin"),
                 checkpoint_raw(checkpoint, "child.status." + side + ".bin"))
        checkpoint_read(checkpoint, "regs." + side + ".bin", backend.registers,
                        deadline, maximum=216)
        if checkpoint["phase"] != "cp0" or side == "before":
            checkpoint_read(checkpoint, "debug." + side + ".bin", backend.debug_registers,
                            deadline, maximum=48)
        append({"op": "sample", "at_ns": backend.clock(),
                "phase": checkpoint["phase"], "side": "a" if side == "before" else "b"})

    def native_backings(checkpoint):
        nonlocal backing_identities
        try:
            rows = backend.acquire_backings(deadline)
        except BaseException:
            checkpoint["backings"] = list(getattr(backend, "last_backings", []))
            for row in checkpoint["backings"]:
                keep(row["content"]["path"], native[row["native_path"]], MAX_MEMORY)
            raise
        checkpoint["backings"] = rows
        actual = {row["native_path"]: row["before"] for row in rows}
        _need(len(rows) == 6 and set(actual) == set(native), "loader_resolution_backing_roster")
        if backing_identities is None:
            backing_identities = actual
        _need(actual == backing_identities, "loader_resolution_backing_identity_changed")
        for row in rows:
            descriptor = keep(row["content"]["path"], native[row["native_path"]], MAX_MEMORY)
            _need(row["content"] == descriptor and row["before"] == row["after"],
                  "loader_resolution_backing_record")

    def derive(checkpoint):
        return decoding.derive_targets(
            maps_bytes=checkpoint_raw(checkpoint, "maps.before.bin"),
            auxv_bytes=checkpoint_raw(checkpoint, "auxv.before.bin"),
            backings=checkpoint["backings"], files=files, native_files=native)

    def pair_stable(checkpoint):
        for kind in ("child.stat", "child.status", "maps", "regs", "auxv"):
            _need(checkpoint_raw(checkpoint, kind + ".before.bin") ==
                  checkpoint_raw(checkpoint, kind + ".after.bin"),
                  "loader_resolution_checkpoint_changed")
        if checkpoint["phase"] != "cp0":
            _need(checkpoint_raw(checkpoint, "debug.before.bin") ==
                  checkpoint_raw(checkpoint, "debug.after.bin"),
                  "loader_resolution_debug_changed")

    def memory_append(packed, address, size, *, append_complete=True):
        """Retain the last failed bounded read as an incomplete packed prefix."""
        try:
            raw = backend.memory(address, size, deadline)
        except BaseException as exc:
            prefix = getattr(exc, "raw_bytes", None)
            if type(prefix) is bytes and 0 < len(prefix) <= size:
                packed.extend(prefix)
            raise
        if append_complete:
            packed.extend(raw)
        return raw

    def stack_sample(checkpoint, rows, sample):
        registers = struct.unpack("<27Q", checkpoint_raw(checkpoint, "regs.before.bin"))
        rsp = registers[19]
        auxv = checkpoint_raw(checkpoint, "auxv.before.bin")
        _need(0 < len(auxv) <= 1024 and len(auxv) % 16 == 0 and rsp % 16 == 0,
              "loader_resolution_initial_stack_extent")
        readout._readable(rows, rsp, 48 + len(auxv))
        side = "before" if sample == 0 else "after"
        raw = checkpoint_read(checkpoint, "stack.words." + side + ".bin", backend.memory,
                              rsp, 48 + len(auxv), deadline, maximum=1072)
        argc, argv0, argv_null, env0, env1, env_null = struct.unpack_from("<6Q", raw)
        _need(argc == 1 and argv_null == env_null == 0 and raw[48:] == auxv,
              "loader_resolution_initial_stack_vectors")
        packed = bytearray()
        try:
            for pointer, expected in zip((argv0, env0, env1), startup.EXPECTED_STRINGS):
                readout._readable(rows, pointer, len(expected))
                memory_append(packed, pointer, len(expected))
                _need(packed[-len(expected):] == expected,
                      "loader_resolution_initial_stack_strings")
        finally:
            descriptor = keep(checkpoint["phase"] + ".stack.strings." + side + ".bin",
                              bytes(packed), 4096)
            checkpoint["raw_files"]["stack.strings." + side + ".bin"] = descriptor

    def native_rx(checkpoint, layouts, native_paths):
        ranges = decoding.rx_ranges(layouts, native_paths)
        checkpoint["native_rx_ranges"] = ranges
        for sample in (0, 1):
            packed = bytearray()
            try:
                for row in ranges:
                    raw = memory_append(packed, row["address"], row["size_bytes"])
                    layout = layouts[row["native_path"]]["rx"]
                    expected = native[row["native_path"]][layout["offset"]:
                        layout["offset"] + layout["filesz"]]
                    _need(raw == expected, "loader_resolution_native_rx_changed")
            finally:
                role = "native.rx.sample" + str(sample) + ".bin"
                checkpoint["raw_files"][role] = keep(checkpoint["phase"] + "." + role,
                                                     bytes(packed), MAX_MEMORY)

    def return_memory(checkpoint, context):
        regs = struct.unpack("<27Q", checkpoint_raw(checkpoint, "regs.before.bin"))
        rows, layouts = context["rows"], context["layouts"]
        ranges, packed = [], bytearray()
        # Resolve only the selected four pointers, all within bounded readable
        # mappings. A failed prefix is retained before the child is killed.
        try:
            readout._readable(rows, regs[5], 40)
            args = memory_append(packed, regs[5], 40)
            ranges.append({"role": "args", "address": regs[5], "offset": 0, "size_bytes": 40})
            consumer, trace_mode, open_mode, _strtab, name, _aux = struct.unpack("<QiiQQQ", args)
            _need(trace_mode == open_mode == 0, "loader_resolution_invocation_modes")
            for role, address in (("consumer_map", consumer), ("provider_map", regs[10])):
                readout._readable(rows, address, 56)
                offset = len(packed)
                memory_append(packed, address, 56)
                ranges.append({"role": role, "address": address,
                               "offset": offset, "size_bytes": 56})
            region = next((row for row in rows if row["start"] <= name < row["end"]), None)
            _need(region is not None and region["permissions"][0] == "r",
                  "loader_resolution_name_mapping")
            maximum = min(256, region["end"] - name)
            raw_name = memory_append(packed, name, maximum, append_complete=False)
            nul = raw_name.find(b"\0")
            if nul < 1:
                packed.extend(raw_name)
                raise CollectionError("loader_resolution_name_terminator")
            raw_name = raw_name[:nul + 1]
            ranges.append({"role": "needed_name", "address": name,
                           "offset": len(packed), "size_bytes": len(raw_name)})
            packed.extend(raw_name)
        finally:
            checkpoint["runtime_ranges"] = ranges
            checkpoint["raw_files"]["memory.sample0.bin"] = keep(
                checkpoint["phase"] + ".memory.sample0.bin", bytes(packed), 131072)
        second = bytearray()
        try:
            for row in ranges:
                memory_append(second, row["address"], row["size_bytes"])
        finally:
            checkpoint["raw_files"]["memory.sample1.bin"] = keep(
                checkpoint["phase"] + ".memory.sample1.bin", bytes(second), 131072)
        _need(packed == second, "loader_resolution_runtime_sample_changed")
        layout = layouts[readout.LOADER]
        rx = layout["rx"]
        checkpoint["loader_rx_range"] = {"address": layout["bias"] + rx["vaddr"],
                                          "size_bytes": rx["filesz"]}
        expected = native[readout.LOADER][rx["offset"]:rx["offset"] + rx["filesz"]]
        for sample in (0, 1):
            raw = checkpoint_read(checkpoint, "loader.rx.sample" + str(sample) + ".bin",
                backend.memory, layout["bias"] + rx["vaddr"], rx["filesz"], deadline,
                maximum=160721)
            _need(raw == expected, "loader_resolution_loader_rx_changed")

    def acquire_point(phase, siginfo=None, sample_started_ns=None):
        checkpoint = point(phase, sample_started_ns)
        shared_roles(checkpoint)
        if siginfo is not None:
            checkpoint["raw_files"]["siginfo.bin"] = keep(phase + ".siginfo.bin", siginfo, 128)
        native_backings(checkpoint)
        sample_state(checkpoint, "before")
        context = derive(checkpoint)
        checkpoint_read(checkpoint, "environment.json", backend.environment, deadline, maximum=65536)
        environment = json.loads(checkpoint_raw(checkpoint, "environment.json"))
        _need(type(environment) is dict and set(environment) == {"cwd_hex", "namespaces", "preload"}
              and environment["cwd_hex"] == "2f"
              and environment["namespaces"] == capture["context"]["namespaces"],
              "loader_resolution_child_environment")
        decoding.validate_preload(environment["preload"], expected=preload_before)
        checkpoint_read(checkpoint, "fds.json", backend.read_proc, "fds", deadline,
                        maximum=limits["max_control_bytes"])
        if phase in ("cp0", "entry"):
            descriptor, raw = backend.executable(deadline)
            checkpoint["executable"] = descriptor
            checkpoint["raw_files"]["executable.elf"] = keep(descriptor["content"]["path"], raw, MAX_MEMORY)
            checkpoint_read(checkpoint, "child.exe.link.bin", backend.read_proc,
                            "exe.link", deadline, maximum=4096)
            if phase == "cp0":
                stack_sample(checkpoint, context["rows"], 0)
            paths = (readout.LAUNCHER, readout.LOADER) if phase == "cp0" else tuple(sorted(native))
            native_rx(checkpoint, context["layouts"], paths)
            if phase == "cp0":
                stack_sample(checkpoint, context["rows"], 1)
        else:
            return_memory(checkpoint, context)
        sample_state(checkpoint, "after")
        pair_stable(checkpoint)
        backend.stable_stop(deadline)
        checkpoint["sample_finished_ns"] = backend.clock()
        return checkpoint, context

    def verify_guard(checkpoints):
        statuses = tuple(checkpoint_raw(checkpoint, "child.status." + side + ".bin")
                         for checkpoint in checkpoints for side in ("before", "after"))
        process = capture["process"]
        return guard_check.validate_installation(
            files["guard.install.json"], files["guard.program.bin"],
            expected_pid=process["child_pid"], expected_parent_pid=process["observer_pid"],
            expected_starttime=process["starttime"],
            expected_launcher_fd=capture["guard"]["launcher_fd"],
            expected_receipt_fd=capture["guard"]["receipt_fd"],
            expected_attempt_id=request["attempt_id"],
            expected_request_sha256=expected_request_sha256,
            setup_status_bytes=files["child.status.setup.bin"],
            setup_fd_records=json.loads(files["child.fds.setup.json"]),
            checkpoint_status_bytes=statuses)

    try:
        keep("request.json", request_bytes, limits["max_control_bytes"])
        keep("source_build.admission.json", _canonical(admitted["source_build_report"]),
             limits["max_control_bytes"])
        keep("original.admission.json", _canonical(admitted["original_admission"]),
             limits["max_control_bytes"])
        _need(backend.source_inventory() == request["sources"],
              "loader_resolution_sources_changed_before_qualification")
        initial_context = backend.context()
        _need(initial_context["observer"] == {key: request["observer"][key]
                                              for key in ("size_bytes", "sha256")},
              "loader_resolution_observer_selection")
        try:
            guard_bytes, hardware_bytes = backend.fresh_qualifications()
        except BaseException:
            for name, raw in getattr(backend, "qualification_files", {}).items():
                if name in ("guard.qualification.json", "two_slot.qualification.json"):
                    keep(name, raw, limits["max_qualification_control_bytes"])
            raise
        keep("guard.qualification.json", guard_bytes, limits["max_qualification_control_bytes"])
        keep("two_slot.qualification.json", hardware_bytes, limits["max_qualification_control_bytes"])
        capture["context"] = backend.context()
        _need(capture["context"] == initial_context, "loader_resolution_qualification_context_changed")
        guard_record = guard_check.validate_qualification(guard_bytes,
            expected_sources=guard.source_bindings(), expected_environment=capture["context"])
        # The guard checker intentionally returns a report rather than its raw
        # record; process/timing joins always use the preserved validated bytes.
        guard_record = json.loads(guard_bytes)
        hardware_report = probe_check.verify_record(record_bytes=hardware_bytes,
            expected_record_sha256=_binding(hardware_bytes)["sha256"],
            expected_context=capture["context"])
        hardware_record = json.loads(hardware_bytes)
        _need(hardware_report["complete_mechanics_verified"],
              "loader_resolution_hardware_qualification_incomplete")
        if native_origin:
            _need(hardware_report["native_record_reconstructed"]
                  and hardware_record["evidence_origin"] == "native_owned_probe",
                  "loader_resolution_hardware_qualification_not_native")
        _need(hardware_record["process"]["observer_pid"] == backend.observer_pid
              and all(row["parent_pid"] == backend.observer_pid for row in guard_record["cases"]),
              "loader_resolution_qualification_observer_pid")
        started = backend.clock()
        _need(guard_record["timing"]["finished_ns"] <= hardware_record["timing"]["started_ns"]
              <= hardware_record["timing"]["finished_ns"] <= started,
              "loader_resolution_qualification_time_order")
        prior_attempts = {row["attempt_id"] for row in guard_record["cases"]}
        prior_attempts.add(hardware_record["attempt_id"])
        _need(request["attempt_id"] not in prior_attempts, "loader_resolution_attempt_reused")
        qualified_observer = proc.parse_proc_stat(bytes.fromhex(
            hardware_record["raw"]["observer.stat.bin"]["hex"]))
        capture["timing"]["started_ns"] = started
        deadline = started + OBSERVATION_NS
        keep("attempt_start.json", _canonical({
            "record_type": "required_gate_idempotence_loader_resolution_attempt_start_v0",
            "profile": admission.PROFILE, "attempt_id": request["attempt_id"],
            "request_sha256": expected_request_sha256, "observer_pid": backend.observer_pid,
            "started_ns": started,
        }), limits["max_control_bytes"])
        keep("guard.program.bin", guard_check.PROGRAM_BYTES, 4096)
        keep("context.before.json", _canonical(capture["context"]), limits["max_control_bytes"])
        read_keep("observer.exe.bin", backend.read_proc, "observer.exe", deadline,
                  maximum=64 * 1024 * 1024)
        _need(_binding(files["observer.exe.bin"]) == capture["context"]["observer"],
              "loader_resolution_observer_executable_changed")
        read_keep("kernel.boot_id.bin", backend.read_proc, "boot_id", deadline, maximum=128)
        for kind in ("stat", "status"):
            read_keep("observer." + kind + ".bin", backend.read_proc,
                      "observer." + kind, deadline)
        observer = proc.parse_proc_stat(files["observer.stat.bin"])
        observer_status = proc.parse_proc_status(files["observer.status.bin"])
        _need(all(observer[key] == qualified_observer[key] for key in ("pid", "starttime", "ppid"))
              and observer["pid"] == observer_status["pid"] == observer_status["tgid"] == backend.observer_pid
              and observer["threads"] == observer_status["threads"] == 1
              and observer_status["tracer"] == 0, "loader_resolution_same_observer_required")
        backend.prepare(native, deadline)
        preload_before = backend.preload(deadline)
        keep("preload.before.json", _canonical(preload_before), limits["max_control_bytes"])
        decoding.validate_preload(preload_before)
        try:
            prelaunch_backings = backend.acquire_backings(deadline)
        except BaseException:
            prefix = list(getattr(backend, "last_backings", []))
            keep("backings.prelaunch.json", _canonical(prefix), limits["max_control_bytes"])
            for row in prefix:
                keep(row["content"]["path"], native[row["native_path"]], MAX_MEMORY)
            raise
        keep("backings.prelaunch.json", _canonical(prelaunch_backings), limits["max_control_bytes"])
        backing_identities = {row["native_path"]: row["before"] for row in prelaunch_backings}
        _need(len(prelaunch_backings) == 6 and set(backing_identities) == set(native),
              "loader_resolution_prelaunch_backings")
        for row in prelaunch_backings:
            descriptor = keep(row["content"]["path"], native[row["native_path"]], MAX_MEMORY)
            _need(row["content"] == descriptor and row["before"] == row["after"],
                  "loader_resolution_prelaunch_backing_read")
        _need(backend.context() == capture["context"]
              and backend.source_inventory() == request["sources"],
              "loader_resolution_prelaunch_context_changed")
        check_time()
        backend.spawn(request["attempt_id"], expected_request_sha256, deadline)
        update_process()
        wait("setup", 0x137F)
        for kind in ("stat", "status"):
            read_keep("child." + kind + ".setup.bin", backend.read_proc,
                      "child." + kind, deadline)
        update_process()
        identity(files["child.stat.setup.bin"], files["child.status.setup.bin"])
        previous_children = {(row["child_pid"], row["starttime"]) for row in guard_record["cases"]}
        previous_children.add((hardware_record["process"]["child_pid"],
                               hardware_record["process"]["starttime"]))
        _need((capture["process"]["child_pid"], capture["process"]["starttime"]) not in previous_children,
              "loader_resolution_child_reused")
        read_keep("child.pidfd.info.bin", backend.read_proc, "pidfd.info", deadline)
        read_keep("guard.install.json", backend.read_proc, "guard.receipt", deadline,
                  maximum=guard_check.MAX_INSTALLATION_BYTES)
        read_keep("child.fds.setup.json", backend.read_proc, "fds", deadline,
                  maximum=limits["max_control_bytes"])
        verify_guard(())
        preload_setup = backend.preload(deadline, child=True)
        keep("preload.setup.json", _canonical(preload_setup), limits["max_control_bytes"])
        decoding.validate_preload(preload_setup, expected=preload_before)
        read_keep("setup.debug.before.bin", backend.debug_registers, deadline, maximum=48)
        _need(files["setup.debug.before.bin"] == initial_debug, "loader_resolution_initial_debug")
        call({"op": "options", "value": PTRACE_OPTIONS}, backend.options)
        resume(0, "setup")
        wait("exec", 0x4057F)
        read_keep("exec.event_message.bin", backend.event_message, deadline, maximum=8)
        _need(files["exec.event_message.bin"] == struct.pack("<Q", capture["process"]["child_pid"]),
              "loader_resolution_exec_pid_changed")
        cp0, cp0_context = acquire_point("cp0")
        _need(checkpoint_raw(cp0, "debug.before.bin") == initial_debug,
              "loader_resolution_cp0_debug")
        target, terminal = cp0_context["return_target"], cp0_context["entry_target"]
        backend.set_targets(target, terminal)
        for number, value in ((0, target), (1, terminal), (6, DR6_RESERVED), (7, 5)):
            write(number, value, "arming")
        armed_debug = struct.pack("<6Q", target, terminal, 0, 0, DR6_RESERVED, 5)
        checkpoint_read(cp0, "debug.armed.bin", backend.debug_registers, deadline, maximum=48)
        _need(checkpoint_raw(cp0, "debug.armed.bin") == armed_debug,
              "loader_resolution_armed_debug")
        cp0["sample_finished_ns"] = backend.clock()
        decoding.validate_checkpoint(checkpoint=cp0, files=files, process=capture["process"],
                                     static_record=static_record, native_files=native)
        verify_guard((cp0,))
        resume(1, "cp0")
        seen = set()
        for number in range(1, 11):
            wait("event.%02d" % number, 0x57F)
            sample_started = backend.clock()
            siginfo = backend.siginfo(deadline)
            regs = backend.registers(deadline)
            debug = backend.debug_registers(deadline)
            _need(len(regs) == 216 and len(debug) == 48 and len(siginfo) == 128,
                  "loader_resolution_stop_raw_extent")
            words = struct.unpack("<27Q", regs)
            pc = words[16]
            if pc == terminal:
                backend.mark_terminal()
                checkpoint, _context = acquire_point("entry", siginfo, sample_started)
                _need(number == 10 and len(seen) == 9, "loader_resolution_early_entry")
            elif pc == target:
                checkpoint, _context = acquire_point("return.%02d" % number, siginfo, sample_started)
                _need(number < 10, "loader_resolution_unexpected_tenth_return")
            else:
                keep("unexpected.regs.bin", regs, 216)
                keep("unexpected.debug.bin", debug, 48)
                keep("unexpected.siginfo.bin", siginfo, 128)
                raise CollectionError("loader_resolution_unexpected_stop_target")
            _need(regs == checkpoint_raw(checkpoint, "regs.before.bin")
                  and debug == checkpoint_raw(checkpoint, "debug.before.bin"),
                  "loader_resolution_stop_sample_changed")
            decoded = decoding.validate_checkpoint(checkpoint=checkpoint, files=files,
                process=capture["process"], static_record=static_record, native_files=native)
            _need(decoded["return_target"] == target and decoded["entry_target"] == terminal,
                  "loader_resolution_targets_changed")
            _need(checkpoint_raw(checkpoint, "auxv.before.bin") ==
                  checkpoint_raw(cp0, "auxv.before.bin"), "loader_resolution_auxv_changed")
            verify_guard((checkpoint,))
            if number < 10:
                join = decoded["occurrence_join"]
                key = (join["consumer"], join["dynamic_entry_ordinal"], join["name"])
                _need(key not in seen, "loader_resolution_duplicate_return")
                seen.add(key)
                # Both breakpoints remain armed after the ninth return.
                resume(number + 1, checkpoint["phase"])
        expected = {(row["consumer"]["path"], row["dynamic_entry_ordinal"], row["name"])
                    for row in static_record["occurrence_bindings"]}
        _need(seen == expected and len(seen) == 9, "loader_resolution_occurrence_coverage")
        complete = True
    except BaseException as exc:
        failure = _failure(exc)
    finally:
        try:
            update_process()
        except BaseException as exc:
            failure = failure or _failure(exc)
        cleanup_started = backend.clock()
        cleanup_deadline = cleanup_started + CLEANUP_NS
        capture["timing"]["cleanup_started_ns"] = cleanup_started
        try:
            for row in backend.cleanup(cleanup_deadline):
                append(row)
        except BaseException as exc:
            for row in getattr(backend, "cleanup_operations", []):
                if row not in capture["operations"]:
                    try:
                        append(row)
                    except (OSError, ValueError):
                        break
            failure = failure or _failure(exc)
        try:
            outputs = backend.drain_outputs(cleanup_deadline)
            for name, raw in outputs.items():
                keep(name, raw, 4096)
            _need(all(raw == b"" for raw in outputs.values()), "loader_resolution_target_output")
        except BaseException as exc:
            for name, raw in getattr(exc, "output_files", {}).items():
                try:
                    keep(name, raw, 4096)
                except (OSError, ValueError):
                    pass
            failure = failure or _failure(exc)
        try:
            update_process()
            after = backend.context()
            keep("context.after.json", _canonical(after), limits["max_control_bytes"])
            _need(capture["context"] is None or after == capture["context"],
                  "loader_resolution_context_changed")
            _need(backend.source_inventory() == request["sources"],
                  "loader_resolution_sources_changed")
        except BaseException as exc:
            failure = failure or _failure(exc)
        try:
            backend.close()
        except BaseException as exc:
            failure = failure or _failure(exc)
        capture["timing"]["finished_ns"] = backend.clock()
    if deadline is not None and cleanup_started > deadline:
        failure = failure or "loader_resolution_deadline"
    if capture["timing"]["finished_ns"] > cleanup_deadline:
        failure = failure or "loader_resolution_cleanup_deadline"
    if not complete:
        failure = failure or "loader_resolution_incomplete_sequence"
    capture["failure"] = failure
    if failure is None:
        capture["status"] = "completed"
    report = None
    # Replay is data-only and runs after cleanup. It reconstructs admission and
    # the raw journal independently; no producer success field can replace it.
    try:
        import check_required_gate_idempotence_loader_resolution_v0 as checker

        def replay():
            encoded = _canonical(capture)
            verifier = checker.verify_capture if native_origin else checker.verify_scripted_capture
            return verifier(request_bytes=request_bytes,
                expected_request_sha256=expected_request_sha256, capture_bytes=encoded,
                expected_capture_sha256=_binding(encoded)["sha256"], files=files,
                admission_inputs=admission_inputs, accepted_policy_sha256=accepted_policy_sha256)

        report = replay()
    except BaseException as exc:
        previously_complete = capture["status"] == "completed"
        capture["status"] = "incomplete"
        capture["failure"] = capture["failure"] or _failure(exc)
        if previously_complete:
            try:
                report = replay()
            except BaseException:
                # Preserve the original bounded raw record even if independent
                # replay rejects the incomplete diagnostic shape as well.
                report = None
    return {"capture": capture, "files": files, "report": report}
