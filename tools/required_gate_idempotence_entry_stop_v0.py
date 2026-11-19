#!/usr/bin/env python3
"""Acquire the original launcher at its bounded executable-entry checkpoint.

Only an explicitly acknowledged fresh attempt can enter this native path.
One owned child installs the selected task guard before exec, stops at cp0,
and is continued once to an x86-64 hardware execution breakpoint. No
instruction at executable entry is resumed. Loader initialization can execute
between the checkpoints; this is not selected-runtime or containment evidence.
"""
from __future__ import annotations

import ctypes
import fcntl
import os
from pathlib import Path
import re
import resource
import signal
import stat
import struct
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_mapping_observation_v0 as shared
import check_required_gate_idempotence_mapping_observation_v0 as mapping_check
import required_gate_idempotence_exec_stop_v0 as prior
import check_required_gate_idempotence_entry_stop_v0 as checker
import check_required_gate_idempotence_entry_task_guard_v0 as guard_check
import required_gate_idempotence_entry_task_guard_v0 as guard

PROFILE, BOUNDARY, LIMITS = checker.PROFILE, checker.BOUNDARY, checker.LIMITS
ACKNOWLEDGEMENT = "OBSERVE_ORIGINAL_LAUNCHER_ENTRY_STOP_ONLY"
LAUNCHER_PATH = "native/bwrap"
NATIVE_LIMIT = 16 * 1024 * 1024
PTRACE_TRACEME, PTRACE_PEEKUSER, PTRACE_POKEUSER = 0, 3, 6
PTRACE_CONT, PTRACE_GETREGS = 7, 12
PTRACE_SETOPTIONS, PTRACE_GETEVENTMSG, PTRACE_GETSIGINFO = 0x4200, 0x4201, 0x4202
PTRACE_OPTIONS = 0x10001e  # EXITKILL | TRACEEXEC | TRACECLONE | TRACEFORK | TRACEVFORK.
DEBUGREG_OFFSET, DR6_RESERVED = 848, 0xffff0ff0
DEBUG_INDICES = (0, 1, 2, 3, 6, 7)
WAIT_FLAGS = os.WNOHANG | os.WUNTRACED | os.WCONTINUED
READ_FLAGS, DIRECTORY_FLAGS = shared.READ_FLAGS, shared.DIRECTORY_FLAGS
_LIBC = ctypes.CDLL(None, use_errno=True)
_LIBC.ptrace.restype = ctypes.c_long
_LIBC.ptrace.argtypes = [ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p]
_LIBC.prctl.restype = ctypes.c_int
_LIBC.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                       ctypes.c_ulong, ctypes.c_ulong]


class EntryStopObservationError(shared.MappingObservationError):
    """A bounded entry attempt failed before independently accepted completion."""


class EntryStopPreservationError(shared.MappingPreservationError):
    code = "entry_stop_preservation_failed"


def _need(condition, code):
    if not condition:
        raise EntryStopObservationError(code)


def _check_deadline(deadline):
    _need(time.monotonic_ns() < deadline, "entry_stop_wall_deadline")


def _failure_code(exc):
    if isinstance(exc, OSError):
        return "entry_stop_os_error_" + str(exc.errno)
    code = getattr(exc, "code", str(exc))
    return code if re.fullmatch(r"[a-z][a-z0-9_]*", code) else "entry_stop_observation_invalid"


class _OutputDirectory(shared._OutputDirectory):
    def preserve(self, name, raw):
        try:
            _need(name in checker.FILE_NAMES and name not in self.files
                  and type(raw) is bytes, "entry_stop_preservation_roster")
            _need(len(raw) <= checker.file_limit(name), "entry_stop_file_size_limit")
            _need(len(self.files) + 2 <= LIMITS["capture_files"]
                  and self.total + len(raw) <= LIMITS["total_capture_bytes"],
                  "entry_stop_capture_size_limit")
            self._check_root()
            identity = shared._write_exclusive(self.fd, name, raw)
            self._check_root()
            self.files[name], self.identities[name] = raw, identity
            self.total += len(raw)
        except (OSError, ValueError) as exc:
            raise EntryStopPreservationError("entry_stop_preservation_failed") from exc

    def publish(self, raw):
        _need(type(raw) is bytes and len(raw) <= LIMITS["control_file_bytes"]
              and self.total + len(raw) <= LIMITS["total_capture_bytes"],
              "entry_stop_capture_size_limit")
        super().publish(raw)

    def mark_failure(self, code):
        try:
            self._check_root()
            raw = checker.canonical({
                "record_type": "required_gate_idempotence_entry_stop_failure_v0",
                "profile": PROFILE, "status": "incomplete", "failure": code, **BOUNDARY,
            })
            shared._write_exclusive(self.fd, "attempt.incomplete.json", raw)
            os.fsync(self.fd)
        except (OSError, ValueError):
            pass  # A failed preservation never publishes an accepted capture.


def _ptrace(request, pid, addr=0, data=0):
    """Preserve the PEEKUSER -1/errno distinction and forbid other writes."""
    _need(request in {PTRACE_TRACEME, PTRACE_PEEKUSER, PTRACE_POKEUSER, PTRACE_CONT,
          PTRACE_GETREGS, PTRACE_SETOPTIONS, PTRACE_GETEVENTMSG, PTRACE_GETSIGINFO},
          "entry_stop_ptrace_request_forbidden")
    if request == PTRACE_PEEKUSER:
        _need(addr in {DEBUGREG_OFFSET + 8 * n for n in DEBUG_INDICES},
              "entry_stop_debug_read_forbidden")
    if request == PTRACE_POKEUSER:
        _need(addr in {DEBUGREG_OFFSET + 8 * n for n in (0, 6, 7)},
              "entry_stop_debug_write_forbidden")
    if request == PTRACE_CONT:
        _need(addr == data == 0, "entry_stop_signal_forwarding_forbidden")
    ctypes.set_errno(0)
    result = _LIBC.ptrace(request, pid, addr, data)
    number = ctypes.get_errno()
    if result == -1 and number:
        raise OSError(number, "ptrace request failed")
    if request == PTRACE_PEEKUSER:
        return result & ((1 << 64) - 1)
    _need(result == 0, "entry_stop_ptrace_return")
    return result


def _registers(pid):
    words = (ctypes.c_uint64 * 27)()
    _ptrace(PTRACE_GETREGS, pid, 0, ctypes.addressof(words))
    return bytes(words)


def _debug_registers(pid):
    return struct.pack("<6Q", *(_ptrace(PTRACE_PEEKUSER, pid, DEBUGREG_OFFSET + 8 * n)
                                  for n in DEBUG_INDICES))


def _siginfo(pid):
    words = (ctypes.c_uint64 * 16)()
    _ptrace(PTRACE_GETSIGINFO, pid, 0, ctypes.addressof(words))
    return bytes(words)


def _event_message(pid):
    value = ctypes.c_ulong()
    _ptrace(PTRACE_GETEVENTMSG, pid, 0, ctypes.addressof(value))
    return value.value


def _read_proc(procfd, name, limit, deadline):
    _check_deadline(deadline)
    fd = os.open(name, READ_FLAGS, dir_fd=procfd)
    try:
        return shared._read_fd(fd, limit, deadline=deadline)
    finally:
        os.close(fd)


def _open_native(path):
    """Pin the ordinary selected file without opening a substituted device."""
    pathfd = os.open(path, os.O_PATH | os.O_CLOEXEC)
    fd = None
    try:
        before = os.fstat(pathfd)
        _need(stat.S_ISREG(before.st_mode), "entry_stop_native_not_regular")
        fd = os.open("/proc/self/fd/" + str(pathfd),
                     os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK)
        _need(shared._stable_identity(before) == shared._stable_identity(os.fstat(fd)),
              "entry_stop_native_object_changed")
        return fd
    except BaseException:
        if fd is not None:
            os.close(fd)
        raise
    finally:
        os.close(pathfd)


def _child_setup(launcherfd, parent_pid, stdoutfd, stderrfd, nullfd, receiptfd,
                 inherited, attempt_id, request_sha256):
    """No original instruction can run before descriptor and guard setup."""
    try:
        os.dup2(nullfd, 0)
        os.dup2(stdoutfd, 1)
        os.dup2(stderrfd, 2)
        for fd in inherited:
            if fd > 2 and fd not in (launcherfd, receiptfd):
                try:
                    os.close(fd)
                except OSError:
                    pass  # Enumeration's transient descriptor may be closed.
        os.setsid()
        os.chdir("/")
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        ctypes.set_errno(0)
        if _LIBC.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "parent death setup failed")
        _need(os.getppid() == parent_pid, "entry_stop_parent_changed")
        guard.install_and_record(receiptfd, launcher_fd=launcherfd,
            parent_pid=parent_pid, attempt_id=attempt_id, request_sha256=request_sha256)
        _ptrace(PTRACE_TRACEME, 0)
        os.kill(os.getpid(), signal.SIGSTOP)
        os.execve("/proc/self/fd/" + str(launcherfd), ["bubblewrap"],
                  {"LC_ALL": "C", "TZ": "UTC"})
    except BaseException as exc:
        try:
            os.write(2, (_failure_code(exc) + "\n").encode("ascii"))
        except OSError:
            pass
    os._exit(120)


def _spawn_child(launcher_fd, parent_pid, attempt_id, request_sha256):
    opened, streams = [], []
    process = None
    try:
        out_r, out_w = os.pipe2(os.O_CLOEXEC)
        opened.extend((out_r, out_w))
        err_r, err_w = os.pipe2(os.O_CLOEXEC)
        opened.extend((err_r, err_w))
        guard_r, guard_w = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
        opened.extend((guard_r, guard_w))
        nullfd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        opened.append(nullfd)
        _need(all(fd > 2 for fd in opened) and launcher_fd > 2,
              "entry_stop_standard_descriptors_unavailable")
        for fd in (out_r, err_r, guard_r):
            streams.append(os.fdopen(fd, "rb", buffering=0))
            opened.remove(fd)
        process = SimpleNamespace(pid=None, stdout=streams[0], stderr=streams[1],
                                  guard_receipt=streams[2], returncode=None,
                                  launcher_fd=launcher_fd, receipt_fd=guard_w)
        inherited = tuple(int(value) for value in os.listdir("/proc/self/fd"))
        _need(os.listdir("/proc/self/task") == [str(parent_pid)],
              "entry_stop_observer_threads")
        pid = os.fork()
        if pid == 0:
            _child_setup(launcher_fd, parent_pid, out_w, err_w, nullfd, guard_w,
                         inherited, attempt_id, request_sha256)
            os._exit(122)
        process.pid = pid
        for fd in (out_w, err_w, guard_w, nullfd):
            os.close(fd)
            opened.remove(fd)
        return process
    except BaseException:
        if process is not None and process.pid is not None:
            # Only our direct, unreaped child is owned here. The caller has not
            # yet received it, so a construction failure must reap it locally.
            _cleanup(process, None, {"wait": {"terminal": None}, "events": [],
                     "ownership": {"child_reaped": False, "kill_sent": False}})
        for stream in streams:
            stream.close()
        raise
    finally:
        for fd in opened:
            os.close(fd)


def _record_wait(capture, process, phase, status):
    terminal = os.WIFEXITED(status) or os.WIFSIGNALED(status)
    if terminal:
        # waitpid has already consumed this child even if preservation cannot
        # append another finite event. Never mislabel the reaped child as live.
        capture["wait"]["terminal"] = status
        capture["ownership"]["child_reaped"] = True
        process.returncode = os.waitstatus_to_exitcode(status)
    _need(len(capture["events"]) < LIMITS["wait_records"], "entry_stop_wait_limit")
    event_msg = None
    if os.WIFSTOPPED(status) and status >> 16:
        event_msg = _event_message(process.pid)
        if status >> 16 == 4:
            capture["wait"]["event_msg"] = event_msg
        elif status >> 16 in (1, 2, 3) and event_msg != process.pid:
            _need(0 < event_msg <= 0x7fffffff and event_msg != os.getpid(),
                  "entry_stop_descendant_identity")
            # A positive task-guard capture cannot reach this path. Retain
            # kernel-reported owned descendants for bounded failure cleanup.
            process.extra_pids = getattr(process, "extra_pids", set()) | {event_msg}
    capture["events"].append({"phase": phase, "pid": process.pid,
                              "status": status, "event_msg": event_msg,
                              "observed_ns": time.monotonic_ns()})
    if phase in capture["wait"]:
        capture["wait"][phase] = status
    return terminal


def _wait_event(process, deadline, capture, phase):
    while True:
        _check_deadline(deadline)
        try:
            got, status = os.waitpid(process.pid, WAIT_FLAGS)
        except InterruptedError:
            continue
        if got:
            _record_wait(capture, process, phase, status)
            return status
        time.sleep(0.002)


def _cleanup(process, pidfd, capture):
    if process is None:
        return None
    extras = set(getattr(process, "extra_pids", ()))
    seen_extras = set(extras)
    if capture["ownership"]["child_reaped"] and not extras:
        return None
    deadline = time.monotonic_ns() + LIMITS["cleanup_seconds"] * 10**9
    failure = "entry_stop_unexpected_task" if extras else None
    # A filter failure must not leave a kernel-reported traced descendant.
    # These PIDs came only from our owned child's fork/clone ptrace event.
    for child in extras:
        try:
            os.kill(child, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            failure = "entry_stop_descendant_cleanup_signal_failed"
    if not capture["ownership"]["child_reaped"]:
        try:
            if pidfd is None:
                failure = failure or "entry_stop_cleanup_pidfd_missing"
                os.kill(process.pid, signal.SIGKILL)
            else:
                signal.pidfd_send_signal(pidfd, signal.SIGKILL)
            capture["ownership"]["kill_sent"] = True
        except ProcessLookupError:
            pass
        except OSError:
            failure = "entry_stop_cleanup_pidfd_signal_failed"
            try:
                os.kill(process.pid, signal.SIGKILL)  # Direct unreaped child only.
                capture["ownership"]["kill_sent"] = True
            except ProcessLookupError:
                pass
            except OSError:
                return "entry_stop_cleanup_signal_failed"
    while time.monotonic_ns() < deadline:
        pending = ([process.pid] if not capture["ownership"]["child_reaped"] else []) + sorted(extras)
        for child in pending:
            try:
                got, status = os.waitpid(child, WAIT_FLAGS | 0x40000000)  # __WALL, only owned PIDs.
            except InterruptedError:
                continue
            except (ChildProcessError, OSError):
                return "entry_stop_cleanup_wait_failed"
            if got:
                terminal = os.WIFEXITED(status) or os.WIFSIGNALED(status)
                if child == process.pid:
                    if terminal:
                        # Reaping must survive even an exhausted event budget.
                        capture["wait"]["terminal"] = status
                        capture["ownership"]["child_reaped"] = True
                        process.returncode = os.waitstatus_to_exitcode(status)
                    if len(capture["events"]) < LIMITS["wait_records"]:
                        try:
                            _record_wait(capture, process, "terminal" if terminal else "unexpected", status)
                        except (OSError, ValueError):
                            # A pending stop can outlive its readable ptrace
                            # metadata after SIGKILL. Retain the raw status and
                            # keep reaping; teardown must not abort here.
                            failure = "entry_stop_cleanup_event_metadata_failed"
                            if len(capture["events"]) < LIMITS["wait_records"]:
                                capture["events"].append({"phase": "unexpected", "pid": child,
                                    "status": status, "event_msg": None,
                                    "observed_ns": time.monotonic_ns()})
                    else:
                        failure = failure or "entry_stop_wait_limit"
                else:
                    if len(capture["events"]) < LIMITS["wait_records"]:
                        capture["events"].append({"phase": "unexpected", "pid": child,
                            "status": status, "event_msg": None, "observed_ns": time.monotonic_ns()})
                    if terminal:
                        extras.remove(child)
        if capture["ownership"]["child_reaped"] and not extras:
            return failure
        new_extras = set(getattr(process, "extra_pids", ())) - seen_extras
        for child in new_extras:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError:
                failure = "entry_stop_descendant_cleanup_signal_failed"
        if new_extras:
            failure = failure or "entry_stop_unexpected_task"
            extras.update(new_extras)
            seen_extras.update(new_extras)
        time.sleep(0.002)
    return "entry_stop_cleanup_deadline"


def _drain_outputs(process, output, failure):
    problem = None
    for name in ("stdout", "stderr"):
        pipe = getattr(process, name) if process is not None else None
        try:
            raw, overflow = shared._drain(pipe, LIMITS[name + "_bytes"])
            output.preserve(name + ".bin", raw)
            if overflow:
                failure = failure or "entry_stop_" + name + "_limit"
        except BaseException as exc:
            problem = problem or exc
        finally:
            if pipe is not None:
                try:
                    pipe.close()
                except BaseException as exc:
                    problem = problem or exc
    if process is not None:
        try:
            if "guard.install.json" not in output.files:
                raw, overflow = shared._drain(process.guard_receipt, guard_check.MAX_INSTALLATION_BYTES)
                output.preserve("guard.install.json", raw)
                if overflow:
                    failure = failure or "entry_stop_guard_receipt_limit"
        except BaseException as exc:
            problem = problem or exc
        finally:
            try:
                process.guard_receipt.close()
            except BaseException as exc:
                problem = problem or exc
    if problem is not None:
        raise problem
    return failure


def _namespaces(procfd):
    result = {}
    for name in guard_check.NAMESPACE_NAMES:
        try:
            result[name] = os.readlink("ns/" + name, dir_fd=procfd)
        except FileNotFoundError:
            if name not in ("time", "time_for_children"):
                raise
            result[name] = None
    return result


def _sealed_launcher(raw):
    fd = os.memfd_create("pulse-entry-stop-launcher-v0", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            _need(count > 0, "entry_stop_launcher_write")
            view = view[count:]
        os.fchmod(fd, 0o500)
        fcntl.fcntl(fd, shared.F_ADD_SEALS, shared.FULL_SEALS)
        _need(fcntl.fcntl(fd, shared.F_GET_SEALS) == shared.FULL_SEALS,
              "entry_stop_launcher_seals")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _snapshot_objects(descriptors, native_files, output, capture, suffix, deadline):
    for role, fd in descriptors.items():
        record, raw = prior._read_regular(fd, NATIVE_LIMIT, deadline)
        if role == "launcher":
            record["seals"] = fcntl.fcntl(fd, shared.F_GET_SEALS)
        output.preserve("native." + role + "." + suffix + ".elf", raw)
        capture["objects"]["native"][role][suffix] = record
        _need(raw == native_files[checker.ROLES[role]], "entry_stop_native_object_mismatch")
        if suffix == "before" and role == "launcher":
            capture["objects"]["retained"] = record
        if suffix == "after":
            _need(record == capture["objects"]["native"][role]["before"],
                  "entry_stop_native_object_changed")


def _checkpoint_snapshot(process, procfd, output, capture, checkpoint, suffix,
                         deadline, child_start):
    for name in ("stat", "status", "maps"):
        output.preserve(checkpoint + ".child." + name + "." + suffix + ".bin",
                        _read_proc(procfd, name, LIMITS["proc_file_bytes"], deadline))
    prior._check_owned_stop(process, capture["observer_pid"],
        output.files[checkpoint + ".child.stat." + suffix + ".bin"],
        output.files[checkpoint + ".child.status." + suffix + ".bin"], child_start)
    output.preserve(checkpoint + ".regs." + suffix + ".bin", _registers(process.pid))
    output.preserve(checkpoint + ".auxv." + suffix + ".bin",
                    _read_proc(procfd, "auxv", LIMITS["proc_file_bytes"], deadline))
    if suffix == "before":
        output.preserve(checkpoint + ".child.exe.link.bin",
                        os.readlink("exe", dir_fd=procfd).encode("utf-8"))
        descriptor, raw = prior._read_executable(procfd, deadline)
        capture["objects"][checkpoint + "_executable"] = descriptor
        output.preserve(checkpoint + ".executable.elf", raw)
        _need(descriptor == capture["objects"]["retained"]
              and raw == output.files["native.launcher.before.elf"],
              "entry_stop_executable_changed")
    else:
        for stem in ("child.maps", "regs", "auxv"):
            _need(output.files[checkpoint + "." + stem + ".before.bin"]
                  == output.files[checkpoint + "." + stem + ".after.bin"],
                  "entry_stop_stopped_snapshot_changed")


def _sample_memory(procfd, spans, output, deadline, capture, checkpoint):
    fd = os.open("mem", READ_FLAGS, dir_fd=procfd)
    try:
        before = os.fstat(fd)
        capture["objects"][checkpoint + "_memory"] = {
            "stat": shared._identity(before), "seals": None}
        _need(stat.S_ISREG(before.st_mode) and before.st_size == 0 and before.st_nlink == 1
              and not before.st_mode & 0o111, "entry_stop_memory_object")
        for sample in (0, 1):
            for role, span in spans.items():
                _check_deadline(deadline)
                raw = os.pread(fd, span["size"], span["address"])
                output.preserve(checkpoint + "." + role + ".rx.sample" + str(sample) + ".bin", raw)
                _need(len(raw) == span["size"], "entry_stop_memory_short_read")
                _need(shared._stable_identity(before) == shared._stable_identity(os.fstat(fd)),
                      "entry_stop_memory_object_changed")
    finally:
        os.close(fd)


def _read_guard_receipt(process):
    raw = bytearray()
    while True:
        try:
            block = os.read(process.guard_receipt.fileno(),
                            min(4096, guard_check.MAX_INSTALLATION_BYTES + 1 - len(raw)))
        except BlockingIOError as exc:
            raise EntryStopObservationError("entry_stop_guard_receipt_not_closed") from exc
        if not block:
            return bytes(raw)
        raw.extend(block)
        _need(len(raw) <= guard_check.MAX_INSTALLATION_BYTES, "entry_stop_guard_receipt_limit")


def _verify_guard(request, capture, files, checkpoints=()):
    child_start = mapping_check.parse_proc_stat(files["child.stat.setup.bin"])["starttime"]
    statuses = tuple(files[point + ".child.status." + suffix + ".bin"]
                     for point in checkpoints for suffix in ("before", "after"))
    return guard_check.validate_installation(files["guard.install.json"], files["guard.program.bin"],
        expected_pid=capture["child_pid"], expected_parent_pid=capture["observer_pid"],
        expected_starttime=child_start, expected_launcher_fd=capture["guard"]["launcher_fd"],
        expected_receipt_fd=capture["guard"]["receipt_fd"], expected_attempt_id=request["attempt_id"],
        expected_request_sha256=capture["request_sha256"],
        setup_status_bytes=files["child.status.setup.bin"],
        setup_fd_records=checker._json(files["child.fds.setup.json"]),
        checkpoint_status_bytes=statuses)


def _check_wait_stable(process, capture, deadline):
    _check_deadline(deadline)
    got, status = os.waitpid(process.pid, WAIT_FLAGS)
    if got:
        _record_wait(capture, process, "unexpected", status)
    _need(not got, "entry_stop_checkpoint_wait_changed")


def _arm_breakpoint(pid, target, output):
    before = _debug_registers(pid)
    output.preserve("cp0.debug.before.bin", before)
    _need(before == struct.pack("<6Q", 0, 0, 0, 0, DR6_RESERVED, 0),
          "entry_stop_initial_debug_state")
    record = {"target": target, "writes": [], "general_register_writes": 0,
              "instruction_pointer_writes": 0, "target_memory_writes": 0}
    try:
        for register, value in ((0, target), (6, DR6_RESERVED), (7, 1)):
            result = _ptrace(PTRACE_POKEUSER, pid, DEBUGREG_OFFSET + 8 * register, value)
            record["writes"].append({"register": register, "value": value,
                                      "returncode": result, "errno": 0})
    finally:
        output.preserve("breakpoint.json", checker.canonical(record))
    armed = _debug_registers(pid)
    output.preserve("cp0.debug.armed.bin", armed)
    _need(armed == struct.pack("<6Q", target, 0, 0, 0, DR6_RESERVED, 1),
          "entry_stop_debug_readback")


def run_acquisition(*, request_bytes, expected_request_sha256, native_files,
                    qualification_bytes, hardware_qualification_bytes,
                    output_directory, acknowledgement):
    """Collect one fresh acknowledged attempt after original-chain admission.

    The public preparation adapter repeats that admission and both pure
    qualification checks. This low-level API also checks the qualifications
    against its fresh actual kernel/boot/namespace/observer context before fork.
    """
    _need(acknowledgement == ACKNOWLEDGEMENT, "entry_stop_owner_acknowledgement_required")
    request = checker.validate_request(request_bytes, expected_request_sha256)
    _need(type(native_files) is dict and set(native_files) == set(checker.NATIVE),
          "entry_stop_original_inventory")
    for path, raw in native_files.items():
        _need(type(raw) is bytes and checker.binding(raw) == checker.NATIVE[path],
              "entry_stop_original_binding")
    _need(sys.platform == "linux" and os.uname().machine == "x86_64"
          and ctypes.sizeof(ctypes.c_ulong) == 8 and os.sysconf("SC_PAGE_SIZE") == 4096,
          "entry_stop_platform_unsupported")
    _need(hasattr(os, "fork") and hasattr(os, "pidfd_open") and hasattr(os, "memfd_create")
          and hasattr(signal, "pidfd_send_signal") and hasattr(os, "O_PATH"),
          "entry_stop_host_api_unsupported")
    actual_context = guard.current_context()
    _need(actual_context["observer"] == {key: request["observer"][key]
                                         for key in ("size_bytes", "sha256")},
          "entry_stop_qualification_observer")
    _need(checker.binding(qualification_bytes) == request["guard"]["qualification"],
          "entry_stop_guard_qualification_binding")
    guard_check.validate_qualification(qualification_bytes,
        expected_sources=guard.source_bindings(), expected_environment=actual_context)
    checker.validate_hardware_qualification(hardware_qualification_bytes,
        request["hardware_qualification"]["sha256"], expected_context=actual_context)
    _need(checker.binding(hardware_qualification_bytes) == request["hardware_qualification"],
          "entry_stop_hardware_qualification_binding")
    guard_record = checker._json(qualification_bytes)
    hardware_record = checker._json(hardware_qualification_bytes)
    preflight_now = time.monotonic_ns()
    _need(guard_record["timing"]["finished_ns"] <= preflight_now
          and hardware_record["timing"]["finished_ns"] <= preflight_now,
          "entry_stop_qualification_from_future")
    prior_attempts = {row["attempt_id"] for row in guard_record["cases"]}
    prior_attempts.update((hardware_record["attempt_id"],
                          "d54f64c544090b13d2c2633b32204e02"))
    _need(request["attempt_id"] not in prior_attempts, "entry_stop_attempt_reused")
    output = _OutputDirectory(output_directory)
    started = time.monotonic_ns()
    deadline = started + LIMITS["wall_seconds"] * 10**9
    parent_pid = os.getpid()
    capture = {
        "record_type": "required_gate_idempotence_entry_stop_capture_v0", "profile": PROFILE,
        "attempt_id": request["attempt_id"], "request_sha256": expected_request_sha256,
        "status": "incomplete", "failure": None, "observer_pid": parent_pid, "child_pid": None,
        "timing": {"started_ns": started, "cp0_ns": None, "entry_ns": None, "finished_ns": None},
        "wait": {"setup": None, "cp0": None, "entry": None, "terminal": None, "event_msg": None},
        "events": [],
        "ownership": {"pidfd_opened": False, "proc_dir_pinned": False, "child_reaped": False,
            "pre_exec_resumes": 0, "cp0_to_entry_resumes": 0, "post_entry_resumes": 0,
            "detached": False, "ptrace_options": 0, "kill_sent": False},
        "guard": {"launcher_fd": None, "receipt_fd": None},
        "objects": {"retained": None, "cp0_executable": None, "entry_executable": None,
            "cp0_memory": None, "entry_memory": None,
            "native": {role: {"before": None, "after": None} for role in checker.ROLES}},
        "files": [], **BOUNDARY,
    }
    process = None
    observerfd = procfd = pidfd = None
    descriptors, identities = {}, {}
    failure = fatal = None
    try:
        try:
            output.preserve("request.json", request_bytes)
            output.preserve("attempt_start.json", checker.canonical({
                "record_type": "required_gate_idempotence_entry_stop_attempt_start_v0",
                "profile": PROFILE, "attempt_id": request["attempt_id"],
                "request_sha256": expected_request_sha256, "observer_pid": parent_pid,
                "started_ns": started,
            }))
            output.preserve("guard.program.bin", guard_check.PROGRAM_BYTES)
            output.preserve("guard.qualification.json", qualification_bytes)
            output.preserve("breakpoint.qualification.json", hardware_qualification_bytes)
            observer, observer_raw = shared._actual_observer()
            output.preserve("observer.exe.bin", observer_raw)
            _need(observer == request["observer"], "entry_stop_observer_selection_mismatch")
            observerfd = os.open("/proc/" + str(parent_pid), DIRECTORY_FLAGS)
            for name in ("stat", "status"):
                output.preserve("observer." + name + ".bin",
                                _read_proc(observerfd, name, LIMITS["proc_file_bytes"], deadline))
            observer_stat = mapping_check.parse_proc_stat(output.files["observer.stat.bin"])
            observer_status = mapping_check.parse_proc_status(output.files["observer.status.bin"])
            _need(observer_stat["pid"] == observer_status["pid"] == observer_status["tgid"] == parent_pid
                  and observer_stat["threads"] == observer_status["threads"] == 1
                  and observer_status["tracer"] == 0, "entry_stop_observer_identity")
            bootfd = os.open("/proc/sys/kernel/random/boot_id", READ_FLAGS)
            try:
                output.preserve("kernel.boot_id.bin", shared._read_fd(bootfd, 128, deadline=deadline))
            finally:
                os.close(bootfd)
            descriptors["launcher"] = _sealed_launcher(native_files[LAUNCHER_PATH])
            for role, path in checker.ROLES.items():
                if role != "launcher":
                    host_path = "/lib64/ld-linux-x86-64.so.2" if role == "loader" else (
                        "/usr/lib/x86_64-linux-gnu/" + Path(path).name)
                    descriptors[role] = _open_native(host_path)
            _snapshot_objects(descriptors, native_files, output, capture, "before", deadline)
            identities = {role: shared._stable_identity(os.fstat(fd)) for role, fd in descriptors.items()}
            output._verify_disk()
            _check_deadline(deadline)
            process = _spawn_child(descriptors["launcher"], parent_pid,
                                   request["attempt_id"], expected_request_sha256)
            capture["child_pid"] = process.pid
            capture["guard"] = {"launcher_fd": process.launcher_fd, "receipt_fd": process.receipt_fd}
            pidfd = os.pidfd_open(process.pid, 0)
            capture["ownership"]["pidfd_opened"] = True
            procfd = os.open("/proc/" + str(process.pid), DIRECTORY_FLAGS)
            capture["ownership"]["proc_dir_pinned"] = True
            _need(_wait_event(process, deadline, capture, "setup") == checker.STOP_WAIT,
                  "entry_stop_setup_missing")
            for name in ("stat", "status"):
                output.preserve("child." + name + ".setup.bin",
                                _read_proc(procfd, name, LIMITS["proc_file_bytes"], deadline))
            child_start = prior._check_owned_stop(process, parent_pid,
                output.files["child.stat.setup.bin"], output.files["child.status.setup.bin"])
            previous_children = {(row["child_pid"], row["starttime"]) for row in guard_record["cases"]}
            hardware_identity = mapping_check.parse_proc_stat(
                bytes.fromhex(hardware_record["raw"]["child.stat.setup.bin"]))
            previous_children.add((hardware_record["child_pid"], hardware_identity["starttime"]))
            _need((process.pid, child_start) not in previous_children,
                  "entry_stop_child_reused")
            output.preserve("guard.install.json", _read_guard_receipt(process))
            output.preserve("child.fds.setup.json", checker.canonical(guard.descriptor_snapshot(process.pid)))
            _verify_guard(request, capture, output.files)
            infofd = os.open("/proc/self/fdinfo/" + str(pidfd), READ_FLAGS)
            try:
                output.preserve("child.pidfd.info.bin",
                                shared._read_fd(infofd, LIMITS["proc_file_bytes"], deadline=deadline))
            finally:
                os.close(infofd)
            _ptrace(PTRACE_SETOPTIONS, process.pid, 0, PTRACE_OPTIONS)
            capture["ownership"]["ptrace_options"] = PTRACE_OPTIONS
            # Recheck every selected original descriptor before any original exec.
            for role, fd in descriptors.items():
                _, raw = prior._read_regular(fd, NATIVE_LIMIT, deadline)
                _need(raw == native_files[checker.ROLES[role]]
                      and shared._stable_identity(os.fstat(fd)) == identities[role],
                      "entry_stop_original_changed_before_exec")
            output._verify_disk()
            _check_deadline(deadline)
            _ptrace(PTRACE_CONT, process.pid)
            capture["ownership"]["pre_exec_resumes"] = 1
            _need(_wait_event(process, deadline, capture, "cp0") == checker.EXEC_WAIT,
                  "entry_stop_exec_event_missing")
            capture["timing"]["cp0_ns"] = time.monotonic_ns()
            _need(capture["wait"]["event_msg"] == process.pid, "entry_stop_exec_pid_changed")
            _checkpoint_snapshot(process, procfd, output, capture, "cp0", "before", deadline, child_start)
            output.preserve("child.fds.cp0.json", checker.canonical(guard.descriptor_snapshot(process.pid)))
            cp0_spans = checker.derive_cp0_spans(request, capture, output.files)
            _sample_memory(procfd, cp0_spans, output, deadline, capture, "cp0")
            _checkpoint_snapshot(process, procfd, output, capture, "cp0", "after", deadline, child_start)
            _verify_guard(request, capture, output.files, ("cp0",))
            _check_wait_stable(process, capture, deadline)
            target = prior.checker._auxv(output.files["cp0.auxv.before.bin"])[9]
            _need(cp0_spans["launcher"]["address"] <= target
                  < cp0_spans["launcher"]["address"] + cp0_spans["launcher"]["size"],
                  "entry_stop_target_outside_launcher_rx")
            _arm_breakpoint(process.pid, target, output)
            output._verify_disk()
            _check_deadline(deadline)
            _ptrace(PTRACE_CONT, process.pid)
            capture["ownership"]["cp0_to_entry_resumes"] = 1
            _need(_wait_event(process, deadline, capture, "entry") == checker.ENTRY_WAIT,
                  "entry_stop_entry_event_missing")
            capture["timing"]["entry_ns"] = time.monotonic_ns()
            output.preserve("entry.siginfo.bin", _siginfo(process.pid))
            output.preserve("entry.debug.before.bin", _debug_registers(process.pid))
            _checkpoint_snapshot(process, procfd, output, capture, "entry", "before", deadline, child_start)
            output.preserve("child.fds.entry.json", checker.canonical(guard.descriptor_snapshot(process.pid)))
            spans = checker.derive_entry_spans(request, capture, output.files)
            _sample_memory(procfd, spans, output, deadline, capture, "entry")
            _snapshot_objects(descriptors, native_files, output, capture, "after", deadline)
            for role, fd in descriptors.items():
                _need(shared._stable_identity(os.fstat(fd)) == identities[role],
                      "entry_stop_native_identity_changed")
            _checkpoint_snapshot(process, procfd, output, capture, "entry", "after", deadline, child_start)
            output.preserve("entry.debug.after.bin", _debug_registers(process.pid))
            _verify_guard(request, capture, output.files, ("cp0", "entry"))
            system = os.uname()
            output.preserve("host.json", checker.canonical({
                "platform": {"system": system.sysname, "machine": system.machine,
                             "release": system.release, "version": system.version},
                "observer_namespaces": _namespaces(observerfd),
                "child_namespaces": _namespaces(procfd),
            }))
            _need(guard.current_context() == actual_context, "entry_stop_host_context_changed")
            _check_wait_stable(process, capture, deadline)
        except shared.MappingPreservationError as exc:
            fatal = exc
        except (OSError, ValueError) as exc:
            failure = _failure_code(exc)
        except BaseException as exc:
            fatal = exc
        finally:
            try:
                failure = _cleanup(process, pidfd, capture) or failure
            except BaseException as exc:
                fatal = fatal or exc
            finally:
                try:
                    failure = _drain_outputs(process, output, failure)
                except BaseException as exc:
                    fatal = fatal or exc
                finally:
                    for fd in (procfd, pidfd, observerfd, *descriptors.values()):
                        if fd is not None:
                            try:
                                os.close(fd)
                            except BaseException as exc:
                                fatal = fatal or exc
        if fatal is not None:
            output.mark_failure("entry_stop_preservation_failed" if isinstance(fatal, shared.MappingPreservationError)
                                else "entry_stop_observation_interrupted")
            raise fatal
        capture["timing"]["finished_ns"] = time.monotonic_ns()
        capture["files"] = [{"path": name, **checker.binding(raw)} for name, raw in sorted(output.files.items())]
        capture["status"], capture["failure"] = ("incomplete" if failure else "completed"), failure
        raw = checker.canonical(capture)
        try:
            report = checker.verify_capture(request_bytes=request_bytes,
                expected_request_sha256=expected_request_sha256, capture_bytes=raw,
                expected_capture_sha256=checker.sha(raw), files=output.files)
        except ValueError as exc:
            if failure is not None:
                raise
            capture["status"], capture["failure"] = "incomplete", _failure_code(exc)
            raw = checker.canonical(capture)
            report = checker.verify_capture(request_bytes=request_bytes,
                expected_request_sha256=expected_request_sha256, capture_bytes=raw,
                expected_capture_sha256=checker.sha(raw), files=output.files)
        output.publish(raw)
        return report
    except BaseException:
        output.mark_failure("entry_stop_capture_not_published")
        raise
    finally:
        output.close()
