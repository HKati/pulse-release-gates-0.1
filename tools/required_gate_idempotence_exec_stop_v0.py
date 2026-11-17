#!/usr/bin/env python3
"""Acquire one explicitly selected original ELF at its kernel exec stop.

The owner acknowledgement permits this bounded acquisition only.  The child
requests tracing before its single original exec.  The observer never resumes
or detaches it after PTRACE_EVENT_EXEC, never writes registers or memory, and
never changes host permissions, capabilities, namespaces or security policy.
The ordinary interpreter file is retained and sampled; it is not sealed and
no immutable history or complete native dependency closure is claimed.
"""
from __future__ import annotations

import ctypes
import fcntl
import os
from pathlib import Path
import re
import signal
import stat
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_mapping_observation_v0 as shared
import check_required_gate_idempotence_mapping_observation_v0 as mapping_check
import check_required_gate_idempotence_exec_stop_v0 as checker

PROFILE, BOUNDARY, LIMITS = checker.PROFILE, checker.BOUNDARY, checker.LIMITS
ACKNOWLEDGEMENT = "OBSERVE_ORIGINAL_LAUNCHER_EXEC_STOP_ONLY"
LAUNCHER_PATH = "native/bwrap"
LOADER_PATH = "native/ld-linux-x86-64.so.2"
INTERPRETER_PATH = "/lib64/ld-linux-x86-64.so.2"
NATIVE_LIMIT = 16 * 1024 * 1024
PTRACE_TRACEME, PTRACE_CONT, PTRACE_GETREGS = 0, 7, 12
PTRACE_SETOPTIONS, PTRACE_GETEVENTMSG = 0x4200, 0x4201
PTRACE_OPTIONS = 0x100010  # EXITKILL | TRACEEXEC, with no target restart at cp0.
WAIT_FLAGS = os.WNOHANG | os.WUNTRACED | os.WCONTINUED
READ_FLAGS, DIRECTORY_FLAGS = shared.READ_FLAGS, shared.DIRECTORY_FLAGS
_LIBC = ctypes.CDLL(None, use_errno=True)
_LIBC.ptrace.restype = ctypes.c_long
_LIBC.ptrace.argtypes = [ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p]
_LIBC.prctl.restype = ctypes.c_int
_LIBC.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                        ctypes.c_ulong, ctypes.c_ulong]


class ExecStopObservationError(shared.MappingObservationError):
    """A selected original acquisition did not satisfy its bounded relation."""


class ExecStopPreservationError(shared.MappingPreservationError):
    code = "exec_stop_preservation_failed"


def _need(condition, code):
    if not condition:
        raise ExecStopObservationError(code)


def _check_deadline(deadline):
    _need(time.monotonic_ns() < deadline, "exec_stop_wall_deadline")


def _failure_code(exc):
    if isinstance(exc, OSError):
        return "exec_stop_os_error_" + str(exc.errno)
    code = getattr(exc, "code", str(exc))
    return code if re.fullmatch(r"[a-z][a-z0-9_]*", code) else "exec_stop_observation_invalid"


class _OutputDirectory(shared._OutputDirectory):
    """Reuse the existing exclusive private, disk-rechecked preservation."""

    def preserve(self, name, raw):
        try:
            _need(name in checker.FILE_NAMES and name not in self.files
                  and type(raw) is bytes, "exec_stop_preservation_roster")
            _need(len(raw) <= checker.file_limit(name), "exec_stop_file_size_limit")
            _need(self.total + len(raw) <= LIMITS["total_capture_bytes"],
                  "exec_stop_capture_size_limit")
            self._check_root()
            identity = shared._write_exclusive(self.fd, name, raw)
            self._check_root()
            self.files[name], self.identities[name] = raw, identity
            self.total += len(raw)
        except (OSError, ValueError) as exc:
            raise ExecStopPreservationError("exec_stop_preservation_failed") from exc

    def mark_failure(self, code):
        try:
            self._check_root()
            raw = checker.canonical({
                "record_type": "required_gate_idempotence_exec_stop_failure_v0",
                "profile": PROFILE, "status": "incomplete", "failure": code, **BOUNDARY,
            })
            shared._write_exclusive(self.fd, "attempt.incomplete.json", raw)
            os.fsync(self.fd)
        except (OSError, ValueError):
            pass  # A preservation failure cannot produce an accepted capture.


def _actual_observer():
    return shared._actual_observer()


def _ptrace(request, pid, addr=0, data=0):
    ctypes.set_errno(0)
    result = _LIBC.ptrace(request, pid, addr, data)
    if result == -1:
        number = ctypes.get_errno()
        raise OSError(number, "ptrace request failed")
    _need(result == 0, "exec_stop_ptrace_return")
    return result


def _registers(pid):
    # Linux x86-64 user_regs_struct: 27 native unsigned 64-bit fields.
    words = (ctypes.c_uint64 * 27)()
    _ptrace(PTRACE_GETREGS, pid, 0, ctypes.addressof(words))
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


def _read_regular(fd, limit, deadline):
    _check_deadline(deadline)
    before = os.fstat(fd)
    os.lseek(fd, 0, os.SEEK_SET)
    raw = shared._read_fd(fd, limit, regular_size=True, deadline=deadline)
    _need(shared._stable_identity(before) == shared._stable_identity(os.fstat(fd)),
          "exec_stop_object_changed")
    return {"stat": shared._identity(before), "seals": None}, raw


def _open_loader():
    """Intentionally follow the selected PT_INTERP, then pin its actual object.

    O_PATH does not activate a substituted FIFO/device.  Only a regular pinned
    object may be reopened through this process's owned descriptor.  This is
    ordinary host resolution, not a map_files acquisition or privilege change.
    """
    pathfd = os.open(INTERPRETER_PATH, os.O_PATH | os.O_CLOEXEC)
    fd = None
    try:
        before = os.fstat(pathfd)
        _need(stat.S_ISREG(before.st_mode), "exec_stop_loader_not_regular")
        fd = os.open("/proc/self/fd/" + str(pathfd),
                     os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK)
        _need(shared._stable_identity(before) == shared._stable_identity(os.fstat(fd)),
              "exec_stop_loader_object_changed")
        return fd
    except BaseException:
        if fd is not None:
            os.close(fd)
        raise
    finally:
        os.close(pathfd)


def _sealed_launcher(raw):
    fd = os.memfd_create("pulse-exec-stop-launcher-v0", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        remaining = memoryview(raw)
        while remaining:
            written = os.write(fd, remaining)
            _need(written > 0, "exec_stop_launcher_write_incomplete")
            remaining = remaining[written:]
        os.fchmod(fd, 0o500)
        fcntl.fcntl(fd, shared.F_ADD_SEALS, shared.FULL_SEALS)
        _need(fcntl.fcntl(fd, shared.F_GET_SEALS) == shared.FULL_SEALS,
              "exec_stop_launcher_seal_mismatch")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_executable(procfd, deadline):
    # This fixed procfs magic link opens the executable object, not its name.
    fd = os.open("exe", os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=procfd)
    try:
        seals = fcntl.fcntl(fd, shared.F_GET_SEALS)
        record, raw = _read_regular(fd, NATIVE_LIMIT, deadline)
        _need(seals == fcntl.fcntl(fd, shared.F_GET_SEALS), "exec_stop_executable_changed")
        record["seals"] = seals
        return record, raw
    finally:
        os.close(fd)


def _child_setup(launcherfd, parent_pid, stdoutfd, stderrfd, nullfd, inherited):
    """Fixed fork child.  Any tracing/setup error exits before original exec."""
    try:
        os.dup2(nullfd, 0)
        os.dup2(stdoutfd, 1)
        os.dup2(stderrfd, 2)
        for fd in inherited:
            if fd > 2 and fd != launcherfd:
                try:
                    os.close(fd)
                except OSError:
                    pass  # /proc/self/fd enumeration's transient FD is gone.
        os.setsid()
        os.chdir("/")
        ctypes.set_errno(0)
        if _LIBC.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "parent death setup failed")
        if os.getppid() != parent_pid:
            os._exit(121)
        _ptrace(PTRACE_TRACEME, 0)
        os.kill(os.getpid(), signal.SIGSTOP)
        # The one setup continuation reaches this exec.  The new image must
        # stop in the kernel before any loader/original userspace instruction.
        os.execve("/proc/self/fd/" + str(launcherfd), ["bubblewrap"],
                  {"LC_ALL": "C", "TZ": "UTC"})
    except OSError as exc:
        try:
            os.write(2, ("exec_stop_child_os_error_" + str(exc.errno) + "\n").encode("ascii"))
        except OSError:
            pass
    except BaseException:
        try:
            os.write(2, b"exec_stop_child_setup_failed\n")
        except OSError:
            pass
    os._exit(120)


def _spawn_child(launcher_fd, parent_pid):
    opened = []
    process = None
    try:
        out_r, out_w = os.pipe2(os.O_CLOEXEC)
        opened.extend((out_r, out_w))
        err_r, err_w = os.pipe2(os.O_CLOEXEC)
        opened.extend((err_r, err_w))
        nullfd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        opened.append(nullfd)
        # Allocate both stream owners before fork.  A parent-side setup error
        # must not lose the direct child before run_acquisition can own it.
        stdout = os.fdopen(out_r, "rb", buffering=0)
        opened.remove(out_r)
        try:
            stderr = os.fdopen(err_r, "rb", buffering=0)
            opened.remove(err_r)
        except BaseException:
            stdout.close()
            raise
        process = SimpleNamespace(pid=None, stdout=stdout, stderr=stderr, returncode=None)
        inherited = tuple(int(value) for value in os.listdir("/proc/self/fd"))
        _need(os.listdir("/proc/self/task") == [str(parent_pid)], "exec_stop_observer_threads")
        pid = os.fork()
        if pid == 0:
            _child_setup(launcher_fd, parent_pid, out_w, err_w, nullfd, inherited)
            os._exit(122)
        process.pid = pid
        for fd in (out_w, err_w, nullfd):
            os.close(fd)
            opened.remove(fd)
        return process
    except BaseException:
        if process is not None:
            if process.pid is not None:
                _cleanup(process, None, {"wait": {"terminal": None},
                         "ownership": {"child_reaped": False, "kill_sent": False}})
            process.stdout.close()
            process.stderr.close()
        raise
    finally:
        for fd in opened:
            os.close(fd)


def _terminal(capture, process, status):
    if os.WIFEXITED(status) or os.WIFSIGNALED(status):
        capture["wait"]["terminal"] = status
        capture["ownership"]["child_reaped"] = True
        process.returncode = os.waitstatus_to_exitcode(status)
        return True
    return False


def _wait_event(process, deadline, capture, phase):
    while True:
        _check_deadline(deadline)
        try:
            got, status = os.waitpid(process.pid, WAIT_FLAGS)
        except InterruptedError:
            continue
        if got:
            capture["wait"][phase] = status
            _terminal(capture, process, status)
            return status
        time.sleep(0.002)


def _check_owned_stop(process, parent_pid, stat_raw, status_raw, expected_start=None):
    record = mapping_check.parse_proc_stat(stat_raw)
    status = mapping_check.parse_proc_status(status_raw)
    _need(record["pid"] == status["pid"] == status["tgid"] == process.pid
          and record["ppid"] == status["ppid"] == parent_pid
          and record["threads"] == status["threads"] == 1
          and record["state"] == status["state"] == "t"
          and status["tracer"] == parent_pid, "exec_stop_child_identity")
    if expected_start is not None:
        _need(record["starttime"] == expected_start, "exec_stop_child_starttime_changed")
    return record["starttime"]


def _cleanup(process, pidfd, capture):
    if process is None or capture["ownership"]["child_reaped"]:
        return None
    deadline = time.monotonic_ns() + LIMITS["cleanup_seconds"] * 10**9
    failure = None
    try:
        if pidfd is None:
            failure = "exec_stop_cleanup_pidfd_missing"
            os.kill(process.pid, signal.SIGKILL)
        else:
            signal.pidfd_send_signal(pidfd, signal.SIGKILL)
        capture["ownership"]["kill_sent"] = True
    except ProcessLookupError:
        pass
    except OSError:
        failure = "exec_stop_cleanup_pidfd_signal_failed"
        try:
            # Only our direct, unreaped child; its PID cannot be reused.
            # This cleanup backstop never qualifies completed observation.
            os.kill(process.pid, signal.SIGKILL)
            capture["ownership"]["kill_sent"] = True
        except ProcessLookupError:
            pass
        except OSError:
            return "exec_stop_cleanup_signal_failed"
    while time.monotonic_ns() < deadline:
        try:
            got, status = os.waitpid(process.pid, WAIT_FLAGS)
        except InterruptedError:
            continue
        except (ChildProcessError, OSError):
            return "exec_stop_cleanup_wait_failed"
        if got and _terminal(capture, process, status):
            return failure
        time.sleep(0.002)
    return "exec_stop_cleanup_deadline"


def _drain_outputs(process, output, capture, failure):
    problem = None
    for name in ("stdout", "stderr"):
        pipe = getattr(process, name) if process is not None else None
        try:
            raw, overflow = shared._drain(pipe, LIMITS[name + "_bytes"])
            output.preserve(name + ".bin", raw)
            if overflow:
                failure = failure or "exec_stop_" + name + "_limit"
        except BaseException as exc:
            problem = problem or exc
        finally:
            if pipe is not None:
                try:
                    pipe.close()
                except BaseException as exc:
                    problem = problem or exc
    if problem is not None:
        raise problem
    return failure


def _sample_memory(procfd, spans, output, deadline, capture):
    fd = os.open("mem", READ_FLAGS, dir_fd=procfd)
    try:
        before = os.fstat(fd)
        capture["objects"]["memory"] = {"stat": shared._identity(before), "seals": None}
        _need(stat.S_ISREG(before.st_mode) and before.st_size == 0 and before.st_nlink == 1
              and not before.st_mode & 0o111,
              "exec_stop_memory_object")
        for sample in (0, 1):
            for name in ("launcher", "loader"):
                _check_deadline(deadline)
                span = spans[name]
                raw = os.pread(fd, span["size"], span["address"])
                output.preserve(name + ".rx.sample" + str(sample) + ".bin", raw)
                _need(len(raw) == span["size"], "exec_stop_memory_short_read")
                _need(shared._stable_identity(before) == shared._stable_identity(os.fstat(fd)),
                      "exec_stop_memory_object_changed")
    finally:
        os.close(fd)


def run_acquisition(*, request_bytes, expected_request_sha256, native_files,
                    output_directory, acknowledgement):
    """Return an independently reconstructed report; never authorize runtime.

    The caller first performs the separate fresh transitive preparation.  This
    function accepts only the two fixed original payloads bound by that request.
    A missing/mismatched acknowledgement fails before any original exec.
    """
    _need(acknowledgement == ACKNOWLEDGEMENT, "exec_stop_owner_acknowledgement_required")
    request = checker.validate_request(request_bytes, expected_request_sha256)
    _need(type(native_files) is dict and set(native_files) == {LAUNCHER_PATH, LOADER_PATH},
          "exec_stop_original_inventory")
    for path, raw in native_files.items():
        _need(type(raw) is bytes and checker.binding(raw) == checker.NATIVE[path],
              "exec_stop_original_binding")
    _need(sys.platform == "linux" and os.uname().machine == "x86_64"
          and ctypes.sizeof(ctypes.c_ulong) == 8 and os.sysconf("SC_PAGE_SIZE") == 4096,
          "exec_stop_platform_unsupported")
    _need(hasattr(os, "fork") and hasattr(os, "pidfd_open") and hasattr(os, "memfd_create")
          and hasattr(signal, "pidfd_send_signal") and hasattr(os, "O_PATH"),
          "exec_stop_host_api_unsupported")
    output = _OutputDirectory(output_directory)
    started = time.monotonic_ns()
    deadline = started + LIMITS["wall_seconds"] * 10**9
    parent_pid = os.getpid()
    capture = {
        "record_type": "required_gate_idempotence_exec_stop_capture_v0", "profile": PROFILE,
        "attempt_id": request["attempt_id"], "request_sha256": expected_request_sha256,
        "status": "incomplete", "failure": None, "observer_pid": parent_pid, "child_pid": None,
        "timing": {"started_ns": started, "stopped_ns": None, "finished_ns": None},
        "wait": {"setup": None, "exec": None, "terminal": None, "event_msg": None},
        "ownership": {"pidfd_opened": False, "proc_dir_pinned": False, "child_reaped": False,
                      "pre_exec_resumes": 0, "ptrace_options": 0, "kill_sent": False,
                      "post_exec_resumes": 0, "detached": False},
        "objects": {"retained": None, "executable": None, "loader_before": None,
                    "loader_after": None, "memory": None},
        "files": [], **BOUNDARY,
    }
    process = None
    loaderfd = launcherfd = observerfd = procfd = pidfd = None
    failure = fatal = None
    try:
        try:
            output.preserve("request.json", request_bytes)
            output.preserve("attempt_start.json", checker.canonical({
                "record_type": "required_gate_idempotence_exec_stop_attempt_start_v0", "profile": PROFILE,
                "attempt_id": request["attempt_id"], "request_sha256": expected_request_sha256,
                "observer_pid": parent_pid, "started_ns": started,
            }))
            output.preserve("launcher.elf", native_files[LAUNCHER_PATH])
            observer, observer_raw = _actual_observer()
            output.preserve("observer.exe.bin", observer_raw)
            _need(observer == request["observer"], "exec_stop_observer_selection_mismatch")
            observerfd = os.open("/proc/self", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            for name in ("stat", "status"):
                output.preserve("observer." + name + ".bin",
                                _read_proc(observerfd, name, LIMITS["proc_file_bytes"], deadline))
            observer_stat = mapping_check.parse_proc_stat(output.files["observer.stat.bin"])
            observer_status = mapping_check.parse_proc_status(output.files["observer.status.bin"])
            _need(observer_stat["pid"] == observer_status["pid"] == observer_status["tgid"] == parent_pid
                  and observer_stat["threads"] == observer_status["threads"] == 1
                  and observer_status["tracer"] == 0, "exec_stop_observer_identity")
            bootfd = os.open("/proc/sys/kernel/random/boot_id", READ_FLAGS)
            try:
                output.preserve("kernel.boot_id.bin", shared._read_fd(bootfd, 128, deadline=deadline))
            finally:
                os.close(bootfd)
            loaderfd = _open_loader()
            loader_identity = shared._stable_identity(os.fstat(loaderfd))
            capture["objects"]["loader_before"], raw = _read_regular(loaderfd, NATIVE_LIMIT, deadline)
            output.preserve("loader.before.elf", raw)
            checker._object(capture["objects"]["loader_before"], "loader")
            _need(raw == native_files[LOADER_PATH], "exec_stop_host_loader_selection_mismatch")
            launcherfd = _sealed_launcher(native_files[LAUNCHER_PATH])
            capture["objects"]["retained"], raw = _read_regular(launcherfd, NATIVE_LIMIT, deadline)
            capture["objects"]["retained"]["seals"] = fcntl.fcntl(launcherfd, shared.F_GET_SEALS)
            output.preserve("retained.elf", raw)
            _need(raw == native_files[LAUNCHER_PATH]
                  and capture["objects"]["retained"]["seals"] == shared.FULL_SEALS,
                  "exec_stop_retained_binding")
            output._verify_disk()
            _check_deadline(deadline)
            process = _spawn_child(launcherfd, parent_pid)
            capture["child_pid"] = process.pid
            pidfd = os.pidfd_open(process.pid, 0)
            capture["ownership"]["pidfd_opened"] = True
            procfd = os.open("/proc/" + str(process.pid), DIRECTORY_FLAGS)
            capture["ownership"]["proc_dir_pinned"] = True
            _need(_wait_event(process, deadline, capture, "setup") == checker.STOP_WAIT,
                  "exec_stop_setup_missing")
            for name in ("stat", "status"):
                output.preserve("child." + name + ".setup.bin",
                                _read_proc(procfd, name, LIMITS["proc_file_bytes"], deadline))
            child_start = _check_owned_stop(process, parent_pid, output.files["child.stat.setup.bin"],
                                            output.files["child.status.setup.bin"])
            _ptrace(PTRACE_SETOPTIONS, process.pid, 0, PTRACE_OPTIONS)
            capture["ownership"]["ptrace_options"] = PTRACE_OPTIONS
            output._verify_disk()
            _, loader_preexec = _read_regular(loaderfd, NATIVE_LIMIT, deadline)
            _need(loader_preexec == native_files[LOADER_PATH]
                  and shared._stable_identity(os.fstat(loaderfd)) == loader_identity,
                  "exec_stop_loader_changed_before_exec")
            _check_deadline(deadline)
            _ptrace(PTRACE_CONT, process.pid)
            capture["ownership"]["pre_exec_resumes"] = 1
            _need(_wait_event(process, deadline, capture, "exec") == checker.EXEC_WAIT,
                  "exec_stop_exec_event_missing")
            capture["timing"]["stopped_ns"] = time.monotonic_ns()
            capture["wait"]["event_msg"] = _event_message(process.pid)
            _need(capture["wait"]["event_msg"] == process.pid, "exec_stop_event_pid_mismatch")
            for name in ("stat", "status", "maps"):
                output.preserve("child." + name + ".before.bin",
                                _read_proc(procfd, name, LIMITS["proc_file_bytes"], deadline))
            _check_owned_stop(process, parent_pid, output.files["child.stat.before.bin"],
                              output.files["child.status.before.bin"], child_start)
            infofd = os.open("/proc/self/fdinfo/" + str(pidfd), READ_FLAGS)
            try:
                output.preserve("child.pidfd.info.bin",
                                shared._read_fd(infofd, LIMITS["proc_file_bytes"], deadline=deadline))
            finally:
                os.close(infofd)
            link = os.readlink("exe", dir_fd=procfd).encode("utf-8")
            output.preserve("child.exe.link.bin", link)
            capture["objects"]["executable"], raw = _read_executable(procfd, deadline)
            output.preserve("executable.elf", raw)
            _need(capture["objects"]["executable"] == capture["objects"]["retained"]
                  and raw == native_files[LAUNCHER_PATH], "exec_stop_executable_object_mismatch")
            output.preserve("regs.before.bin", _registers(process.pid))
            output.preserve("auxv.before.bin", _read_proc(procfd, "auxv", LIMITS["proc_file_bytes"], deadline))
            spans = checker.derive_spans(request, capture, output.files)
            _sample_memory(procfd, spans, output, deadline, capture)
            capture["objects"]["loader_after"], raw = _read_regular(loaderfd, NATIVE_LIMIT, deadline)
            output.preserve("loader.after.elf", raw)
            _need(raw == native_files[LOADER_PATH]
                  and shared._stable_identity(os.fstat(loaderfd)) == loader_identity,
                  "exec_stop_loader_changed")
            output.preserve("regs.after.bin", _registers(process.pid))
            output.preserve("auxv.after.bin", _read_proc(procfd, "auxv", LIMITS["proc_file_bytes"], deadline))
            for name in ("maps", "status", "stat"):
                output.preserve("child." + name + ".after.bin",
                                _read_proc(procfd, name, LIMITS["proc_file_bytes"], deadline))
            _check_owned_stop(process, parent_pid, output.files["child.stat.after.bin"],
                              output.files["child.status.after.bin"], child_start)
            system = os.uname()
            output.preserve("host.json", checker.canonical({
                "platform": {"system": system.sysname, "machine": system.machine,
                             "release": system.release, "version": system.version},
                "observer_namespaces": shared._namespaces(observerfd),
                "child_namespaces": shared._namespaces(procfd),
            }))
            _check_deadline(deadline)
            got, status = os.waitpid(process.pid, WAIT_FLAGS)
            if got:
                _terminal(capture, process, status)
            _need(not got, "exec_stop_checkpoint_wait_changed")
        except shared.MappingPreservationError as exc:
            fatal = exc
        except (OSError, ValueError) as exc:
            failure = _failure_code(exc)
        except BaseException as exc:
            fatal = exc
        finally:
            failure = _cleanup(process, pidfd, capture) or failure
            try:
                failure = _drain_outputs(process, output, capture, failure)
            except BaseException as exc:
                fatal = fatal or exc
            for fd in (procfd, pidfd, observerfd, launcherfd, loaderfd):
                if fd is not None:
                    os.close(fd)
        if fatal is not None:
            output.mark_failure("exec_stop_preservation_failed" if isinstance(fatal, shared.MappingPreservationError)
                                else "exec_stop_observation_interrupted")
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
        output.mark_failure("exec_stop_capture_not_published")
        raise
    finally:
        output.close()
