#!/usr/bin/env python3
"""Install or qualify the entry observer's fixed child task-creation guard.

Only install_and_record mutates the calling process. Its caller must already
be the owned disposable child with exact standard streams and sealed launcher.
The separate qualifier executes small authored diagnostic probes, never the
selected original launcher or any selected original native object.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import fcntl
import mmap
import os
from pathlib import Path
import resource
import signal
import stat
import struct
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_entry_task_guard_v0 as checker

ROOT = Path(__file__).resolve().parents[1]
F_GET_SEALS, F_ADD_SEALS = 1034, 1033
TaskGuardError = checker.TaskGuardError
_need = checker._need
_LIBC = ctypes.CDLL(None, use_errno=True)
_LIBC.prctl.restype = ctypes.c_int
_LIBC.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                        ctypes.c_ulong, ctypes.c_ulong]
_LIBC.mprotect.restype = ctypes.c_int
_LIBC.mprotect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]


def program_instructions():
    """Build a fixed denylist independently of the checker's golden bytes."""
    rows = [(0x20, 0, 0, 4), (0x15, 1, 0, 0xC000003E), (0x06, 0, 0, 0x80000000),
            (0x20, 0, 0, 0), (0x45, 0, 1, 0x40000000), (0x06, 0, 0, 0x80000000)]
    for number in (56, 57, 58, 425, 426, 427, 435):
        rows.extend(((0x15, 0, 1, number), (0x06, 0, 0, 0x80000000)))
    rows.append((0x06, 0, 0, 0x7FFF0000))
    return tuple(rows)


def program_bytes():
    return b"".join(struct.pack("<HBBI", *row) for row in program_instructions())


def _platform():
    _need(sys.platform == "linux" and os.uname().machine == "x86_64"
          and sys.byteorder == "little" and ctypes.sizeof(ctypes.c_void_p) == 8
          and ctypes.sizeof(ctypes.c_ulong) == 8, "entry_guard_platform_unsupported")


def _read(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        result = bytearray()
        while True:
            block = os.read(fd, min(65536, maximum + 1 - len(result)))
            if not block:
                return bytes(result)
            result.extend(block)
            _need(len(result) <= maximum, "entry_guard_read_limit")
    finally:
        os.close(fd)


def _stat_record(info):
    return {"dev": info.st_dev, "ino": info.st_ino, "mode": info.st_mode,
            "rdev": info.st_rdev, "size": info.st_size}


def descriptor_snapshot(pid):
    """Return a sorted array of actual procfs FD records for one owned task.

    A self enumeration excludes its own opened directory and the already closed
    transient descriptor used by os.listdir. An externally stopped child's
    descriptor disappearance is an error, never an ignored roster member.
    """
    checker._integer(pid, "entry_guard_descriptor_pid", 1)
    prefix = "/proc/" + str(pid)
    own = pid == os.getpid()
    scanfd = os.open(prefix + "/fd", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        entries = os.listdir(scanfd)
        _need(len(entries) <= checker.MAX_FDS + 2, "entry_guard_descriptor_count")
        _need(all(value.isdecimal() for value in entries), "entry_guard_descriptor_name")
        records = []
        for fd in sorted(int(value) for value in entries):
            if own and fd == scanfd:
                continue
            path = prefix + "/fd/" + str(fd)
            try:
                link = os.readlink(path)
                before = _stat_record(os.stat(path))
            except FileNotFoundError:
                if own:
                    continue
                raise
            seals = None
            if stat.S_ISREG(before["mode"]):
                duplicate = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK)
                try:
                    _need(_stat_record(os.fstat(duplicate)) == before,
                          "entry_guard_descriptor_changed")
                    try:
                        seals = fcntl.fcntl(duplicate, F_GET_SEALS)
                    except OSError as exc:
                        if exc.errno != errno.EINVAL:
                            raise
                finally:
                    os.close(duplicate)
            info = _read(prefix + "/fdinfo/" + str(fd), 4096)
            _need(_stat_record(os.stat(path)) == before and os.readlink(path) == link,
                  "entry_guard_descriptor_changed")
            records.append({"fd": fd, "link": link, "fdinfo": info.decode("ascii"),
                            "stat": before, "seals": seals})
        return records
    finally:
        os.close(scanfd)


def _prctl(option, arg2=0, arg3=0):
    ctypes.set_errno(0)
    result = _LIBC.prctl(option, arg2, arg3, 0, 0)
    return {"option": option, "arg2": arg2, "result": result,
            "errno": ctypes.get_errno()}


def _install_program():
    class Instruction(ctypes.Structure):
        _fields_ = [("code", ctypes.c_uint16), ("jt", ctypes.c_uint8),
                    ("jf", ctypes.c_uint8), ("k", ctypes.c_uint32)]

    class Program(ctypes.Structure):
        _fields_ = [("length", ctypes.c_uint16), ("filter", ctypes.POINTER(Instruction))]

    rows = program_instructions()
    array = (Instruction * len(rows))(*(Instruction(*row) for row in rows))
    program = Program(len(rows), array)
    _need(ctypes.sizeof(Instruction) == 8 and ctypes.sizeof(Program) == 16
          and Program.filter.offset == 8 and bytes(array) == checker.PROGRAM_BYTES,
          "entry_guard_program_abi")
    calls = []
    for option, arg2, arg3, expected in (
        (38, 1, 0, 0), (39, 0, 0, 1),
        (22, 2, ctypes.addressof(program), 0), (21, 0, 0, 2), (39, 0, 0, 1),
    ):
        call = _prctl(option, arg2, arg3)
        calls.append(call)
        _need(call["result"] == expected and call["errno"] == 0,
              "entry_guard_prctl_" + str(option) + "_failed")
    return calls


def install_and_record(receipt_fd, *, launcher_fd, parent_pid, attempt_id, request_sha256):
    """Install in the owned child and close its sole evidence pipe on return.

    The exact filter bytes are submitted through the source-bound installer.
    A successful return is corroborated by raw prctl results and a one-filter
    procfs increment. This is intentionally not kernel filter-byte readback.
    The receipt is nonblocking and bounded by actual empty-pipe capacity, so a
    parent waiting for the later setup stop cannot deadlock on a full pipe.
    """
    checker._integer(receipt_fd, "entry_guard_receipt_fd", 3, (1 << 20) - 1)
    try:
        _platform()
        checker._integer(launcher_fd, "entry_guard_launcher_fd", 3, (1 << 20) - 1)
        _need(launcher_fd != receipt_fd and os.getppid() == parent_pid,
              "entry_guard_child_owner")
        _need(type(attempt_id) is str and len(attempt_id) == 32
              and all(c in "0123456789abcdef" for c in attempt_id)
              and type(request_sha256) is str and len(request_sha256) == 64
              and all(c in "0123456789abcdef" for c in request_sha256),
              "entry_guard_request_identity")
        _need(program_bytes() == checker.PROGRAM_BYTES, "entry_guard_program_mismatch")
        proc_stat = _read("/proc/self/stat", checker.PROC_BYTES)
        identity = checker.parse_stat(proc_stat)
        _need(identity["pid"] == os.getpid() and identity["ppid"] == parent_pid
              and identity["threads"] == 1, "entry_guard_child_identity")
        records = descriptor_snapshot(os.getpid())
        checker.validate_descriptors(records, (0, 1, 2, launcher_fd, receipt_fd),
                                     launcher_fd, receipt_fd)
        before = _read("/proc/self/status", checker.PROC_BYTES)
        before_fields = checker.parse_status(before)
        _need(before_fields["TracerPid"] == 0, "entry_guard_installer_already_traced")
        calls = _install_program()
        after = _read("/proc/self/status", checker.PROC_BYTES)
        after_fields = checker.parse_status(after)
        _need(after_fields["NoNewPrivs"] == 1 and after_fields["Seccomp"] == 2
              and after_fields["Seccomp_filters"] == before_fields["Seccomp_filters"] + 1,
              "entry_guard_installation_unconfirmed")
        record = {"record_type": checker.INSTALLATION_TYPE, "profile": checker.PROFILE,
            "attempt_id": attempt_id, "request_sha256": request_sha256,
            "parent_pid": parent_pid, "child_pid": os.getpid(),
            "starttime": identity["starttime"], "launcher_fd": launcher_fd,
            "receipt_fd": receipt_fd, "program": checker.program_binding(),
            "program_instruction_count": checker.PROGRAM_INSTRUCTION_COUNT,
            "calls": calls, "proc_stat": proc_stat.decode("ascii"),
            "status_before": before.decode("ascii"), "status_after": after.decode("ascii"),
            "fd_roster": records, "physical_authentication": False,
            "privileged_filter_readback": False, "authority_effect": "none"}
        raw = checker.canonical(record)
        capacity = fcntl.fcntl(receipt_fd, fcntl.F_GETPIPE_SZ)
        _need(len(raw) <= min(checker.MAX_INSTALLATION_BYTES, capacity),
              "entry_guard_receipt_capacity")
        os.set_blocking(receipt_fd, False)
        rest = memoryview(raw)
        while rest:
            written = os.write(receipt_fd, rest)
            _need(written > 0, "entry_guard_receipt_write_incomplete")
            rest = rest[written:]
        return record
    finally:
        os.close(receipt_fd)


def source_bindings():
    return [{"path": path, **checker.binding(_read(ROOT / path, 1024 * 1024))}
            for path in checker.SOURCE_PATHS]


def current_context(observer_descriptor=None):
    """Read this environment; it does not qualify a hosted target environment."""
    _platform()
    observer = checker.binding(_read("/proc/self/exe", 64 * 1024 * 1024))
    if observer_descriptor is not None:
        checker._same(observer, observer_descriptor, "entry_guard_observer_selection_mismatch")
    uname = os.uname()
    namespaces = {}
    for name in checker.NAMESPACE_NAMES:
        try:
            namespaces[name] = os.readlink("/proc/self/ns/" + name)
        except FileNotFoundError:
            if name not in ("time", "time_for_children"):
                raise
            namespaces[name] = None
    value = {"uname": {"sysname": uname.sysname, "release": uname.release,
                        "version": uname.version, "machine": uname.machine},
             "boot_id": _read("/proc/sys/kernel/random/boot_id", 128).decode("ascii").strip(),
             "observer": observer,
             "namespaces": namespaces}
    return checker.validate_environment(value)


environment_identity = current_context


def _sealed_probe():
    raw = checker.exec_probe_bytes()
    fd = os.memfd_create("pulse-entry-task-guard-qualification-v0",
                         os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        remaining = memoryview(raw)
        while remaining:
            count = os.write(fd, remaining)
            _need(count > 0, "entry_guard_probe_write")
            remaining = remaining[count:]
        os.fchmod(fd, 0o500)
        fcntl.fcntl(fd, F_ADD_SEALS, checker.FULL_SEALS)
        _need(fcntl.fcntl(fd, F_GET_SEALS) == checker.FULL_SEALS, "entry_guard_probe_seals")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _close_unselected(keep):
    for text in os.listdir("/proc/self/fd"):
        fd = int(text)
        if fd > 2 and fd not in keep:
            try:
                os.close(fd)
            except OSError as exc:
                if exc.errno != errno.EBADF:
                    raise


def _run_probe(name):
    code = checker.probe_bytes(name)
    region = mmap.mmap(-1, mmap.PAGESIZE, flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,
                       prot=mmap.PROT_READ | mmap.PROT_WRITE)
    region[:len(code)] = code
    address = ctypes.addressof(ctypes.c_char.from_buffer(region))
    ctypes.set_errno(0)
    _need(_LIBC.mprotect(address, mmap.PAGESIZE, mmap.PROT_READ | mmap.PROT_EXEC) == 0,
          "entry_guard_probe_executable_mapping")
    ctypes.CFUNCTYPE(None)(address)()
    os._exit(126)  # Every authored probe terminates in machine code.


def _deadline(deadline):
    _need(time.monotonic_ns() < deadline, "entry_guard_qualification_deadline")


def _wait(pid, deadline, *, stop=False):
    flags = os.WNOHANG | (os.WUNTRACED if stop else 0)
    while True:
        _deadline(deadline)
        try:
            got, status = os.waitpid(pid, flags)
        except InterruptedError:
            continue
        if got:
            return status
        time.sleep(0.002)


def _drain(fd, maximum):
    os.set_blocking(fd, False)
    result = bytearray()
    while True:
        try:
            block = os.read(fd, min(4096, maximum + 1 - len(result)))
        except BlockingIOError as exc:
            raise TaskGuardError("entry_guard_pipe_writer_not_closed") from exc
        if not block:
            return bytes(result)
        result.extend(block)
        _need(len(result) <= maximum, "entry_guard_pipe_limit")


class _QualificationFailure(TaskGuardError):
    def __init__(self, code, record):
        super().__init__(code)
        self.record = record


def _qualify_case(name, overall_deadline):
    started = time.monotonic_ns()
    deadline = min(overall_deadline, started + checker.QUALIFICATION_LIMITS["case_seconds"] * 10**9)
    parent_pid, pid, pidfd, reaped = os.getpid(), None, None, False
    opened = set()
    row = {"name": name, "parent_pid": parent_pid,
           "attempt_id": uuid.uuid4().hex,
           "request_sha256": checker.binding(("entry-task-guard:" + name).encode("ascii"))["sha256"],
           "probe": checker.binding(checker.exec_probe_bytes() if name == "exec_survival_clone"
                                     else checker.probe_bytes(name)),
           "child_reaped": False, "cleanup_signal_sent": False, "resumes": 0,
           "timing": {"started_ns": started, "setup_ns": None,
                      "resumed_ns": None, "finished_ns": None}}
    error = None
    receipt_r = out_r = err_r = None
    try:
        _deadline(deadline)
        _need(os.listdir("/proc/self/task") == [str(parent_pid)],
              "entry_guard_qualification_observer_threads")
        launcher_fd = _sealed_probe()
        opened.add(launcher_fd)
        receipt_r, receipt_w = os.pipe2(os.O_CLOEXEC)
        opened.update((receipt_r, receipt_w))
        out_r, out_w = os.pipe2(os.O_CLOEXEC)
        opened.update((out_r, out_w))
        err_r, err_w = os.pipe2(os.O_CLOEXEC)
        opened.update((err_r, err_w))
        nullfd = os.open("/dev/null", os.O_RDONLY | os.O_CLOEXEC)
        opened.add(nullfd)
        _need(all(fd > 2 for fd in opened), "entry_guard_standard_descriptors_unavailable")
        row.update(launcher_fd=launcher_fd, receipt_fd=receipt_w)
        pid = os.fork()
        if pid == 0:
            try:
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
                resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
                os.dup2(nullfd, 0)
                os.dup2(out_w, 1)
                os.dup2(err_w, 2)
                _close_unselected({launcher_fd, receipt_w})
                os.setsid()
                call = _prctl(1, signal.SIGKILL)
                _need(call["result"] == 0 and os.getppid() == parent_pid,
                      "entry_guard_qualification_parent_lost")
                install_and_record(receipt_w, launcher_fd=launcher_fd, parent_pid=parent_pid,
                                   attempt_id=row["attempt_id"], request_sha256=row["request_sha256"])
                os.kill(os.getpid(), signal.SIGSTOP)
                if name == "exec_survival_clone":
                    os.execve("/proc/self/fd/" + str(launcher_fd), ["entry-task-guard-probe"],
                              {"LC_ALL": "C", "TZ": "UTC"})
                _run_probe(name)
            except BaseException as exc:
                code = getattr(exc, "code", "entry_guard_qualification_child_failed")
                try:
                    os.write(2, (str(code)[:120] + "\n").encode("ascii", "replace"))
                except OSError:
                    pass
            os._exit(120)
        row["child_pid"] = pid
        for fd in (receipt_w, out_w, err_w, nullfd):
            os.close(fd)
            opened.remove(fd)
        pidfd = os.pidfd_open(pid, 0)
        opened.add(pidfd)
        status = _wait(pid, deadline, stop=True)
        row["setup_wait_status"] = status
        if os.WIFEXITED(status) or os.WIFSIGNALED(status):
            reaped = row["child_reaped"] = True
            row["terminal_wait_status"] = status
        _need(status == (signal.SIGSTOP << 8) | 127, "entry_guard_qualification_setup_failed")
        row["timing"]["setup_ns"] = time.monotonic_ns()
        install = _drain(receipt_r, checker.MAX_INSTALLATION_BYTES)
        row["installation"] = install.decode("ascii")
        stat_raw = _read("/proc/" + str(pid) + "/stat", checker.PROC_BYTES)
        row["starttime"] = checker.parse_stat(stat_raw)["starttime"]
        setup = _read("/proc/" + str(pid) + "/status", checker.PROC_BYTES)
        row["setup_status"] = setup.decode("ascii")
        row["setup_fds"] = descriptor_snapshot(pid)
        checker.validate_installation(install, checker.PROGRAM_BYTES,
            expected_pid=pid, expected_parent_pid=parent_pid, expected_starttime=row["starttime"],
            expected_launcher_fd=launcher_fd, expected_receipt_fd=receipt_w,
            expected_attempt_id=row["attempt_id"], expected_request_sha256=row["request_sha256"],
            setup_status_bytes=setup, setup_fd_records=row["setup_fds"])
        _deadline(deadline)
        signal.pidfd_send_signal(pidfd, signal.SIGCONT)
        row["resumes"] = 1
        row["timing"]["resumed_ns"] = time.monotonic_ns()
        status = _wait(pid, deadline)
        row["terminal_wait_status"] = status
        reaped = row["child_reaped"] = True
        _need((os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0) if name == "native_getpid"
              else (os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGSYS),
              "entry_guard_qualification_denial_not_observed")
    except BaseException as exc:
        error = getattr(exc, "code", "entry_guard_qualification_os_error_" + str(getattr(exc, "errno", 0)))
    finally:
        if pid is not None and not reaped:
            try:
                if pidfd is not None:
                    signal.pidfd_send_signal(pidfd, signal.SIGKILL)
                else:
                    os.kill(pid, signal.SIGKILL)  # Owned, unreaped direct child only.
                row["cleanup_signal_sent"] = True
            except ProcessLookupError:
                pass
            except OSError:
                error = "entry_guard_qualification_cleanup_signal_failed"
            try:
                status = _wait(pid, time.monotonic_ns()
                               + checker.QUALIFICATION_LIMITS["cleanup_seconds"] * 10**9)
                row["terminal_wait_status"] = status
                row["child_reaped"] = os.WIFEXITED(status) or os.WIFSIGNALED(status)
                if not row["child_reaped"]:
                    error = "entry_guard_qualification_cleanup_incomplete"
            except (OSError, TaskGuardError):
                error = "entry_guard_qualification_cleanup_failed"
        for key, fd, maximum in (("stdout_hex", out_r, 4096), ("stderr_hex", err_r, 4096),
                                 ("installation", receipt_r, checker.MAX_INSTALLATION_BYTES)):
            if fd is not None and fd in opened and key not in row:
                try:
                    raw = _drain(fd, maximum)
                    row[key] = raw.decode("ascii") if key == "installation" else raw.hex()
                except (OSError, ValueError):
                    error = "entry_guard_qualification_evidence_incomplete"
        row["timing"]["finished_ns"] = time.monotonic_ns()
        for fd in opened:
            try:
                os.close(fd)
            except OSError:
                error = "entry_guard_qualification_descriptor_close_failed"
    if error is not None:
        raise _QualificationFailure(error, row)
    return row


def qualify():
    """Bounded, separate diagnostic qualification; returns incomplete on failure."""
    started = time.monotonic_ns()
    deadline = started + checker.QUALIFICATION_LIMITS["wall_seconds"] * 10**9
    result = {"record_type": checker.QUALIFICATION_TYPE, "profile": checker.PROFILE,
              "status": "incomplete", "failure": None, "program": checker.program_binding(),
              "sources": [], "environment": None,
              "limits": dict(checker.QUALIFICATION_LIMITS), "cases": [],
              "timing": {"started_ns": started, "finished_ns": None}, **checker.BOUNDARY}
    try:
        _platform()
        result["sources"] = source_bindings()
        result["environment"] = current_context()
        _need(hasattr(os, "fork") and hasattr(os, "memfd_create") and hasattr(os, "pidfd_open")
              and hasattr(signal, "pidfd_send_signal"), "entry_guard_qualification_api_unsupported")
        for name in checker.QUALIFICATION_CASES:
            _deadline(deadline)
            result["cases"].append(_qualify_case(name, deadline))
        checker._same(source_bindings(), result["sources"], "entry_guard_qualification_sources_changed")
        checker._same(current_context(), result["environment"], "entry_guard_qualification_context_changed")
        result["timing"]["finished_ns"] = time.monotonic_ns()
        result["status"] = "complete"
        checker.validate_qualification(checker.canonical(result),
            expected_sources=result["sources"], expected_environment=result["environment"])
    except BaseException as exc:
        if isinstance(exc, _QualificationFailure):
            result["cases"].append(exc.record)
        result["status"] = "incomplete"
        result["failure"] = getattr(exc, "code", "entry_guard_qualification_failed")
        result["timing"]["finished_ns"] = time.monotonic_ns()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("qualify",))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = qualify()
    raw = checker.canonical(report)
    if args.output is None:
        sys.stdout.buffer.write(raw)
    else:
        with args.output.open("xb") as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
