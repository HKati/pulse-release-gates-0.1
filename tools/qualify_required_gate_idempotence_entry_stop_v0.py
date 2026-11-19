#!/usr/bin/env python3
"""Qualify the selected hardware-stop ABI with a fixed inert authored ELF.

The 130-byte static ELF has only a UD2 instruction, no interpreter and no
syscalls. The instruction must not execute: the sole continuation from the
kernel exec checkpoint must stop at the hardware breakpoint first. This is a
separate owned capability test, never an original-launcher acquisition.
"""
from __future__ import annotations

import argparse
import ctypes
import fcntl
import os
from pathlib import Path
import resource
import signal
import struct
import sys
import time
from types import SimpleNamespace
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_required_gate_idempotence_entry_stop_v0 as checker
import required_gate_idempotence_entry_stop_v0 as native
import required_gate_idempotence_entry_task_guard_v0 as guard

SOURCE_PATHS = tuple(sorted((
    "tools/check_required_gate_idempotence_entry_stop_v0.py",
    "tools/check_required_gate_idempotence_entry_task_guard_v0.py",
    "tools/required_gate_idempotence_entry_stop_v0.py",
    "tools/required_gate_idempotence_entry_task_guard_v0.py",
    "tools/qualify_required_gate_idempotence_entry_stop_v0.py",
)))


def probe_bytes():
    header = struct.pack("<16sHHIQQQIHHHHHH",
        b"\x7fELF\x02\x01\x01" + bytes(9), 2, 62, 1, 0x400080, 64, 0, 0,
        64, 56, 1, 0, 0, 0)
    segment = struct.pack("<IIQQQQQQ", 1, 5, 0, 0x400000, 0x400000, 130, 130, 4096)
    return header + segment + bytes(8) + b"\x0f\x0b"


def _probe_child(fd, parent_pid, inherited):
    try:
        nullfd = os.open("/dev/null", os.O_RDWR | os.O_CLOEXEC)
        for target in (0, 1, 2):
            os.dup2(nullfd, target)
        for candidate in (*inherited, nullfd):
            if candidate > 2 and candidate != fd:
                try:
                    os.close(candidate)
                except OSError:
                    pass
        os.setsid()
        os.chdir("/")
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        ctypes.set_errno(0)
        native._need(native._LIBC.prctl(1, signal.SIGKILL, 0, 0, 0) == 0
                     and os.getppid() == parent_pid, "entry_hardware_parent_guard")
        native._ptrace(native.PTRACE_TRACEME, 0)
        os.kill(os.getpid(), signal.SIGSTOP)
        os.execve("/proc/self/fd/" + str(fd), ["pulse-entry-hardware-probe"],
                  {"LC_ALL": "C", "TZ": "UTC"})
    except OSError as exc:
        # Preserve bounded setup errno in the owned child's raw exit status;
        # the parent can distinguish an unavailable ptrace ABI from a trap.
        os._exit(160 + min(max(exc.errno or 0, 0), 63))
    except BaseException:
        os._exit(120)


def qualify():
    native._need(sys.platform == "linux" and os.uname().machine == "x86_64"
                 and ctypes.sizeof(ctypes.c_ulong) == 8 and os.sysconf("SC_PAGE_SIZE") == 4096,
                 "entry_hardware_platform")
    parent_pid = os.getpid()
    native._need(os.listdir("/proc/self/task") == [str(parent_pid)],
                 "entry_hardware_observer_threads")
    started = time.monotonic_ns()
    deadline = started + 15 * 10**9
    context = guard.current_context()
    sources = [{"path": path, **checker.binding(checker._source(path))} for path in SOURCE_PATHS]
    probe = probe_bytes()
    record = {
        "record_type": "required_gate_idempotence_entry_stop_hardware_qualification_v0",
        "profile": "linux_x86_64_entry_stop_hardware_qualification_v0",
        "status": "incomplete", "failure": None, "attempt_id": uuid.uuid4().hex,
        "context": context, "sources": sources, "probe": checker.binding(probe),
        "observer_pid": parent_pid, "child_pid": None,
        "wait": {"setup": None, "cp0": None, "entry": None, "terminal": None, "event_msg": None},
        "events": [], "raw": {},
        "ownership": {"pidfd_opened": False, "proc_dir_pinned": False, "child_reaped": False,
            "pre_exec_resumes": 0, "cp0_to_entry_resumes": 0, "post_entry_resumes": 0,
            "detached": False, "ptrace_options": 0, "kill_sent": False},
        "timing": {"started_ns": started, "cp0_ns": None, "entry_ns": None, "finished_ns": None},
        "breakpoint": {"target": 0x400080, "writes": [], "general_register_writes": 0,
            "instruction_pointer_writes": 0, "target_memory_writes": 0},
        **checker.HARDWARE_BOUNDARY,
    }
    process = None
    fd = pidfd = procfd = observerfd = None
    failure = fatal = None

    def raw(name, value):
        native._need(type(value) is bytes and len(value) <= 65536,
                     "entry_hardware_raw_limit")
        record["raw"][name] = value.hex()

    try:
        observerfd = os.open("/proc/" + str(parent_pid), native.DIRECTORY_FLAGS)
        for name in ("stat", "status"):
            raw("observer." + name + ".bin", native._read_proc(observerfd, name, 65536, deadline))
        fd = os.memfd_create("pulse-entry-hardware-ud2-v0", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        view = memoryview(probe)
        while view:
            count = os.write(fd, view)
            native._need(count > 0, "entry_hardware_probe_write")
            view = view[count:]
        os.fchmod(fd, 0o500)
        fcntl.fcntl(fd, native.shared.F_ADD_SEALS, native.shared.FULL_SEALS)
        native._need(fcntl.fcntl(fd, native.shared.F_GET_SEALS) == native.shared.FULL_SEALS,
                     "entry_hardware_probe_seals")
        inherited = tuple(int(name) for name in os.listdir("/proc/self/fd"))
        process = SimpleNamespace(pid=None, returncode=None)
        pid = os.fork()
        if pid == 0:
            _probe_child(fd, parent_pid, inherited)
            os._exit(122)
        process.pid = pid
        record["child_pid"] = pid
        pidfd = os.pidfd_open(pid, 0)
        record["ownership"]["pidfd_opened"] = True
        procfd = os.open("/proc/" + str(pid), native.DIRECTORY_FLAGS)
        record["ownership"]["proc_dir_pinned"] = True
        setup = native._wait_event(process, deadline, record, "setup")
        reason = "entry_hardware_setup_stop"
        if os.WIFEXITED(setup) and 160 <= os.WEXITSTATUS(setup) <= 223:
            reason = "entry_hardware_child_os_error_" + str(os.WEXITSTATUS(setup) - 160)
        native._need(setup == checker.STOP_WAIT, reason)
        for name in ("stat", "status"):
            raw("child." + name + ".setup.bin", native._read_proc(procfd, name, 65536, deadline))
        infofd = os.open("/proc/self/fdinfo/" + str(pidfd), native.READ_FLAGS)
        try:
            raw("child.pidfd.info.bin", native.shared._read_fd(infofd, 65536, deadline=deadline))
        finally:
            os.close(infofd)
        native._ptrace(native.PTRACE_SETOPTIONS, pid, 0, native.PTRACE_OPTIONS)
        record["ownership"]["ptrace_options"] = native.PTRACE_OPTIONS
        native._ptrace(native.PTRACE_CONT, pid)
        record["ownership"]["pre_exec_resumes"] = 1
        native._need(native._wait_event(process, deadline, record, "cp0") == checker.EXEC_WAIT,
                     "entry_hardware_exec_stop")
        record["timing"]["cp0_ns"] = time.monotonic_ns()
        for name in ("stat", "status"):
            raw("cp0.child." + name + ".bin", native._read_proc(procfd, name, 65536, deadline))
        raw("cp0.regs.bin", native._registers(pid))
        raw("cp0.auxv.bin", native._read_proc(procfd, "auxv", 65536, deadline))
        _descriptor, executable = native.prior._read_executable(procfd, deadline)
        raw("executable.elf", executable)
        native._need(executable == probe, "entry_hardware_probe_mismatch")
        raw("cp0.debug.before.bin", native._debug_registers(pid))
        for number, value in ((0, 0x400080), (6, native.DR6_RESERVED), (7, 1)):
            code = native._ptrace(native.PTRACE_POKEUSER, pid, native.DEBUGREG_OFFSET + 8 * number, value)
            record["breakpoint"]["writes"].append({"register": number, "value": value,
                                                    "returncode": code, "errno": 0})
        raw("cp0.debug.armed.bin", native._debug_registers(pid))
        native._need(bytes.fromhex(record["raw"]["cp0.debug.armed.bin"])
                     == struct.pack("<6Q", 0x400080, 0, 0, 0, native.DR6_RESERVED, 1),
                     "entry_hardware_debug_readback")
        native._check_deadline(deadline)
        native._ptrace(native.PTRACE_CONT, pid)
        record["ownership"]["cp0_to_entry_resumes"] = 1
        native._need(native._wait_event(process, deadline, record, "entry") == checker.ENTRY_WAIT,
                     "entry_hardware_entry_stop")
        record["timing"]["entry_ns"] = time.monotonic_ns()
        for name in ("stat", "status"):
            raw("entry.child." + name + ".bin", native._read_proc(procfd, name, 65536, deadline))
        raw("entry.regs.bin", native._registers(pid))
        raw("entry.auxv.bin", native._read_proc(procfd, "auxv", 65536, deadline))
        raw("entry.debug.bin", native._debug_registers(pid))
        raw("entry.siginfo.bin", native._siginfo(pid))
        memfd = os.open("mem", native.READ_FLAGS, dir_fd=procfd)
        try:
            raw("entry.memory.bin", os.pread(memfd, 2, 0x400080))
        finally:
            os.close(memfd)
        native._check_deadline(deadline)
    except (OSError, ValueError) as exc:
        failure = native._failure_code(exc)
    except BaseException as exc:
        fatal = exc
    finally:
        try:
            if process is not None and process.pid is not None:
                failure = native._cleanup(process, pidfd, record) or failure
        except BaseException as exc:
            failure = native._failure_code(exc)
        finally:
            for descriptor in (procfd, pidfd, fd, observerfd):
                if descriptor is not None:
                    try:
                        os.close(descriptor)
                    except BaseException as exc:
                        failure = native._failure_code(exc)
    if fatal is not None:
        failure = failure or "entry_hardware_observation_interrupted"
    record["timing"]["finished_ns"] = time.monotonic_ns()
    record["status"], record["failure"] = ("incomplete" if failure else "completed"), failure
    if failure is None:
        try:
            native._need(context == guard.current_context(), "entry_hardware_context_changed")
            native._need(sources == [{"path": path, **checker.binding(checker._source(path))}
                                    for path in SOURCE_PATHS], "entry_hardware_sources_changed")
            encoded = checker.canonical(record)
            checker.validate_hardware_qualification(encoded, checker.sha(encoded), expected_context=context)
        except (OSError, ValueError) as exc:
            record["status"], record["failure"] = "incomplete", native._failure_code(exc)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        record = qualify()
        encoded = checker.canonical(record)
        native._need(len(encoded) <= 1024 * 1024, "entry_hardware_record_limit")
        checker.old.write_new(args.output, encoded)
        sys.stdout.buffer.write(checker.canonical({
            "record_type": "required_gate_idempotence_entry_stop_hardware_qualification_result_v0",
            "status": "accepted" if record["status"] == "completed" else "rejected",
            "qualification": checker.binding(encoded), "failure": record["failure"],
            **checker.HARDWARE_BOUNDARY,
        }))
        return 0 if record["status"] == "completed" else 1
    except (OSError, ValueError) as exc:
        sys.stdout.buffer.write(checker.canonical({"status": "rejected",
            "error_code": native._failure_code(exc), **checker.HARDWARE_BOUNDARY}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
