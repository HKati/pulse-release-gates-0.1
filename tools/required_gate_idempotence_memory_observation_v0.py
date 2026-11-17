#!/usr/bin/env python3
"""Observe one fixed private-data transition in the built-in authored probe.

The selected static ELF stops twice.  Only after preserving and checking the
first checkpoint does this collector issue its one continuation.  It reads
the two fixed virtual-memory pages independently of their sealed backing
object, then kills and reaps the child after the second checkpoint.  There
is no supplied executable, arbitrary address, original launcher/runtime,
ptrace operation, or privilege/security-policy change in this profile.

The kernel, procfs, observer and its Python environment remain trusted.  The
two checkpoints do not authenticate signal senders, intermediate instruction
history, physical page residency, or the rest of the process address space.
"""
from __future__ import annotations

import argparse
import fcntl
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import required_gate_idempotence_mapping_observation_v0 as shared
import required_gate_idempotence_memory_probe_v0 as probe
import check_required_gate_idempotence_memory_observation_v0 as checker

PROFILE = checker.PROFILE
BOUNDARY = checker.BOUNDARY
LIMITS = checker.LIMITS
READ_FLAGS = shared.READ_FLAGS
DIRECTORY_FLAGS = shared.DIRECTORY_FLAGS
WAIT_FLAGS = shared.WAIT_FLAGS
F_ADD_SEALS, F_GET_SEALS, FULL_SEALS = shared.F_ADD_SEALS, shared.F_GET_SEALS, shared.FULL_SEALS


class MemoryObservationError(shared.MappingObservationError):
    """A bounded observation could not satisfy its selected relation."""


class MemoryPreservationError(shared.MappingPreservationError):
    code = "memory_preservation_failed"


def _need(condition, code):
    if not condition:
        raise MemoryObservationError(code)


def _check_deadline(deadline):
    _need(time.monotonic_ns() < deadline, "memory_wall_deadline")


def _failure_code(exc):
    if isinstance(exc, (shared.MappingObservationError, checker.MemoryCheckError)):
        code = getattr(exc, "code", str(exc))
        return code if re.fullmatch(r"[a-z][a-z0-9_]*", code) else "memory_observation_invalid"
    if isinstance(exc, OSError):
        return "memory_os_error_" + str(exc.errno)
    return "memory_observation_invalid"


class _OutputDirectory(shared._OutputDirectory):
    """Reuse exclusive private preservation, with this profile's raw roster."""

    def preserve(self, name, raw):
        try:
            _need(name in checker.FILE_NAMES and name not in self.files
                  and type(raw) is bytes, "memory_preservation_roster")
            _need(len(raw) <= checker.file_limit(name), "memory_file_size_limit")
            _need(self.total + len(raw) <= LIMITS["total_capture_bytes"], "memory_capture_size_limit")
            self._check_root()
            identity = shared._write_exclusive(self.fd, name, raw)
            self._check_root()
            self.files[name] = raw
            self.identities[name] = identity
            self.total += len(raw)
        except (OSError, ValueError) as exc:
            raise MemoryPreservationError("memory_preservation_failed") from exc

    def mark_failure(self, code):
        try:
            self._check_root()
            raw = checker.canonical({
                "record_type": "required_gate_idempotence_memory_failure_v0",
                "profile": PROFILE, "status": "incomplete", "failure": code, **BOUNDARY,
            })
            shared._write_exclusive(self.fd, "attempt.incomplete.json", raw)
            os.fsync(self.fd)
        except (OSError, ValueError):
            pass  # A preservation failure never publishes an accepted capture.


def _preserve(output, name, raw):
    output.preserve(name, raw)


def make_selection(attempt_id):
    _need(type(attempt_id) is str and re.fullmatch(r"[0-9a-f]{32}", attempt_id) is not None,
          "memory_attempt_id_invalid")
    observer, _ = shared._actual_observer()
    raw = checker.canonical({
        "record_type": "required_gate_idempotence_memory_selection_v0", "profile": PROFILE,
        "attempt_id": attempt_id, "probe": checker.binding(probe.probe_bytes()),
        "observer": observer, "sources": checker.source_bindings(), "limits": dict(LIMITS),
        "checkpoints": list(checker.CHECKPOINTS),
        "ranges": [dict(item) for item in checker.RANGES],
        "transition": dict(checker.TRANSITION), **BOUNDARY,
    })
    checker.validate_selection(raw, checker.sha(raw))
    return raw


def _sealed_probe(raw):
    fd = os.memfd_create("pulse-memory-probe-v0", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            _need(count > 0, "memory_probe_write_incomplete")
            view = view[count:]
        os.fchmod(fd, 0o500)
        fcntl.fcntl(fd, F_ADD_SEALS, FULL_SEALS)
        _need(fcntl.fcntl(fd, F_GET_SEALS) == FULL_SEALS, "memory_probe_seal_mismatch")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _spawn_probe(fd, parent_pid):
    return subprocess.Popen(
        ["pulse-memory-probe-v0", probe.parent_argument(parent_pid)],
        executable="/proc/self/fd/" + str(fd), stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
        pass_fds=(fd,), env=dict(shared.ENVIRONMENT), cwd="/", start_new_session=True,
    )


def _read_object(fd):
    before = os.fstat(fd)
    seals = fcntl.fcntl(fd, F_GET_SEALS)
    os.lseek(fd, 0, os.SEEK_SET)
    raw = shared._read_fd(fd, checker.ELF_BYTES, regular_size=True)
    _need(shared._stable_identity(before) == shared._stable_identity(os.fstat(fd))
          and seals == fcntl.fcntl(fd, F_GET_SEALS), "memory_executable_changed")
    return {"stat": shared._identity(before), "seals": seals}, raw


def _read_executable(proc_fd):
    # This fixed procfs magic link opens the child's actual executable object.
    # The displayed pathname is never used to acquire a replacement object.
    fd = os.open("exe", os.O_RDONLY | os.O_CLOEXEC, dir_fd=proc_fd)
    try:
        return _read_object(fd)
    finally:
        os.close(fd)


def _wait_for_stop(process, capture, checkpoint, deadline):
    while True:
        _check_deadline(deadline)
        try:
            got, status = os.waitpid(process.pid, WAIT_FLAGS)
        except InterruptedError:
            continue
        if not got:
            time.sleep(0.002)
            continue
        checkpoint["wait_status"] = status
        # WCONTINUED is optional: the next stop can supersede its pending
        # notification.  It is permitted only after our sole successful send.
        if os.WIFCONTINUED(status):
            _need(checkpoint["checkpoint_id"] == "cp1"
                  and capture["ownership"]["continuations_sent"] == 1
                  and capture["timing"]["continued_ns"] is not None
                  and capture["wait"]["continued"] is None, "memory_unexpected_continuation")
            capture["wait"]["continued"] = status
            continue
        shared._terminal(capture, process, status)
        _need(os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGSTOP,
              "memory_expected_stop_missing")
        checkpoint["stopped_ns"] = time.monotonic_ns()
        _check_deadline(deadline)
        return


def _quiet_wait(process, capture, checkpoint, deadline):
    _check_deadline(deadline)
    got, status = os.waitpid(process.pid, WAIT_FLAGS)
    if got:
        checkpoint["observation_wait"] = status
        shared._terminal(capture, process, status)
    _need(not got, "memory_checkpoint_wait_changed")
    _check_deadline(deadline)


def _read_memory_pages(proc_fd, capture, checkpoint, output, deadline):
    prefix = checkpoint["checkpoint_id"] + "."
    _check_deadline(deadline)
    fd = os.open("mem", READ_FLAGS, dir_fd=proc_fd)
    try:
        before = os.fstat(fd)
        _need(stat.S_ISREG(before.st_mode) and before.st_ino > 0
              and before.st_nlink == 1 and before.st_size == 0,
              "memory_descriptor_invalid")
        identity = shared._identity(before)
        checkpoint["memory_object"] = identity
        if checkpoint["checkpoint_id"] == "cp1":
            _need(identity == capture["checkpoints"][0]["memory_object"],
                  "memory_descriptor_changed_between_checkpoints")
        for reading in ("first", "second"):
            for item in checker.RANGES:
                _check_deadline(deadline)
                raw = os.pread(fd, item["size_bytes"], item["address"])
                # Preserve exactly what the kernel returned before rejecting
                # a short read.  No backing-file substitution or retry exists.
                _preserve(output, prefix + item["range_id"] + "." + reading + ".bin", raw)
                _need(len(raw) == item["size_bytes"], "memory_page_read_incomplete")
                _check_deadline(deadline)
        _need(shared._stable_identity(before) == shared._stable_identity(os.fstat(fd)),
              "memory_descriptor_changed_during_read")
    finally:
        os.close(fd)


def _observe_checkpoint(process, pidfd, procfd, observerfd, capture, checkpoint,
                        output, deadline, probe_raw):
    prefix = checkpoint["checkpoint_id"] + "."
    _wait_for_stop(process, capture, checkpoint, deadline)
    for name in ("stat", "status", "maps"):
        _check_deadline(deadline)
        _preserve(output, prefix + "child." + name + ".before.bin",
                  shared._read_proc(procfd, name, LIMITS["proc_file_bytes"]))
    _check_deadline(deadline)
    infofd = os.open("/proc/self/fdinfo/" + str(pidfd), READ_FLAGS)
    try:
        _preserve(output, prefix + "child.pidfd.info.bin",
                  shared._read_fd(infofd, LIMITS["proc_file_bytes"]))
    finally:
        os.close(infofd)
    link = os.readlink("exe", dir_fd=procfd).encode("utf-8")
    _need(0 < len(link) <= LIMITS["proc_file_bytes"], "memory_executable_link_limit")
    _preserve(output, prefix + "child.exe.link.bin", link)
    _check_deadline(deadline)
    checkpoint["executable_object"], executable_raw = _read_executable(procfd)
    _preserve(output, prefix + "executable.elf", executable_raw)
    _need(checkpoint["executable_object"] == capture["objects"]["retained_before"]
          and executable_raw == probe_raw, "memory_executable_object_mismatch")
    system = os.uname()
    host = {"platform": {"system": system.sysname, "machine": system.machine,
                         "release": system.release, "version": system.version},
            "observer_namespaces": shared._namespaces(observerfd),
            "child_namespaces": shared._namespaces(procfd)}
    _preserve(output, prefix + "host.json", checker.canonical(host))
    _read_memory_pages(procfd, capture, checkpoint, output, deadline)
    for name in ("maps", "status", "stat"):
        _check_deadline(deadline)
        _preserve(output, prefix + "child." + name + ".after.bin",
                  shared._read_proc(procfd, name, LIMITS["proc_file_bytes"]))
    _quiet_wait(process, capture, checkpoint, deadline)
    checker.verify_checkpoint(capture, output.files, checkpoint["checkpoint_id"])
    _check_deadline(deadline)
    output._verify_disk()
    # Disk preservation is part of the checkpoint, and can itself take time.
    # Recheck both the wall limit and wait state before granting continuation.
    _quiet_wait(process, capture, checkpoint, deadline)
    checkpoint["observed_ns"] = time.monotonic_ns()
    checkpoint["preserved"] = True


def _new_checkpoint(checkpoint_id):
    return {"checkpoint_id": checkpoint_id, "stopped_ns": None, "observed_ns": None,
            "wait_status": None, "observation_wait": None, "executable_object": None,
            "memory_object": None, "preserved": False}


def run_example(*, selection_bytes, expected_selection_sha256, output_directory):
    selection = checker.validate_selection(selection_bytes, expected_selection_sha256)
    observer, observer_bytes = shared._actual_observer()
    _need(observer == selection["observer"], "memory_observer_selection_mismatch")
    _need(hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal")
          and hasattr(os, "memfd_create") and hasattr(os, "pread"), "memory_host_api_unsupported")
    raw = probe.probe_bytes()
    _need(len(raw) == checker.ELF_BYTES and checker.binding(raw) == selection["probe"],
          "memory_probe_selection_mismatch")
    output = _OutputDirectory(output_directory)
    started = time.monotonic_ns()
    wall_deadline = started + LIMITS["wall_seconds"] * 10**9
    parent_pid = os.getpid()
    capture = {
        "record_type": "required_gate_idempotence_memory_capture_v0", "profile": PROFILE,
        "attempt_id": selection["attempt_id"], "selection_sha256": expected_selection_sha256,
        "status": "incomplete", "failure": None, "observer_pid": parent_pid, "child_pid": None,
        "timing": {"started_ns": started, "continued_ns": None, "finished_ns": None},
        "wait": {"continued": None, "terminal": None},
        "ownership": {"pidfd_opened": False, "proc_dir_pinned": False,
                      "child_reaped": False, "continuations_sent": 0},
        "objects": {"retained_before": None, "retained_after": None},
        "checkpoints": [_new_checkpoint(item) for item in checker.CHECKPOINTS],
        "files": [], **BOUNDARY,
    }
    process = None
    pidfd = procfd = observerfd = retained_fd = None
    failure = None
    fatal = None
    try:
        try:
            _preserve(output, "selection.json", selection_bytes)
            _preserve(output, "attempt_start.json", checker.canonical({
                "record_type": "required_gate_idempotence_memory_attempt_start_v0", "profile": PROFILE,
                "attempt_id": selection["attempt_id"], "selection_sha256": expected_selection_sha256,
                "observer_pid": parent_pid, "started_ns": started,
            }))
            _preserve(output, "probe.elf", raw)
            _preserve(output, "observer.exe.bin", observer_bytes)
            observerfd = os.open("/proc/self", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            for name in ("stat", "status"):
                _check_deadline(wall_deadline)
                _preserve(output, "observer." + name + ".bin",
                          shared._read_proc(observerfd, name, LIMITS["proc_file_bytes"]))
            bootfd = os.open("/proc/sys/kernel/random/boot_id", READ_FLAGS)
            try:
                _preserve(output, "kernel.boot_id.bin", shared._read_fd(bootfd, 128))
            finally:
                os.close(bootfd)
            retained_fd = _sealed_probe(raw)
            capture["objects"]["retained_before"], retained_raw = _read_object(retained_fd)
            _preserve(output, "retained.before.elf", retained_raw)
            _need(retained_raw == raw, "memory_retained_probe_mismatch")
            _check_deadline(wall_deadline)
            process = _spawn_probe(retained_fd, parent_pid)
            capture["child_pid"] = process.pid
            pidfd = os.pidfd_open(process.pid, 0)
            capture["ownership"]["pidfd_opened"] = True
            procfd = os.open("/proc/" + str(process.pid), DIRECTORY_FLAGS)
            capture["ownership"]["proc_dir_pinned"] = True
            cp0, cp1 = capture["checkpoints"]
            _observe_checkpoint(process, pidfd, procfd, observerfd, capture, cp0,
                                output, wall_deadline, raw)
            _need(cp0["preserved"] and cp0["observed_ns"] is not None
                  and capture["ownership"]["continuations_sent"] == 0,
                  "memory_continuation_precondition")
            _quiet_wait(process, capture, cp0, wall_deadline)
            signal.pidfd_send_signal(pidfd, signal.SIGCONT)
            capture["ownership"]["continuations_sent"] = 1
            capture["timing"]["continued_ns"] = time.monotonic_ns()
            _observe_checkpoint(process, pidfd, procfd, observerfd, capture, cp1,
                                output, wall_deadline, raw)
        except shared.MappingPreservationError as exc:
            fatal = exc
        except (OSError, ValueError) as exc:
            failure = _failure_code(exc)
        except BaseException as exc:
            fatal = exc
        finally:
            try:
                cleanup_failure = shared._cleanup(process, pidfd, capture, wall_deadline)
                failure = cleanup_failure or failure
            except BaseException as exc:
                fatal = fatal or exc
                # A Python-level interruption must not skip cleanup of our
                # owned child.  This retries cleanup only, never the attempt.
                try:
                    cleanup_failure = shared._cleanup(process, pidfd, capture, wall_deadline)
                    failure = cleanup_failure or failure
                except BaseException as cleanup_exc:
                    fatal = fatal or cleanup_exc
            if retained_fd is not None:
                try:
                    capture["objects"]["retained_after"], retained_after = _read_object(retained_fd)
                    _preserve(output, "retained.after.elf", retained_after)
                    _need(capture["objects"]["retained_after"] == capture["objects"]["retained_before"]
                          and retained_after == raw, "memory_retained_object_changed")
                except shared.MappingPreservationError as exc:
                    fatal = fatal or exc
                except (OSError, ValueError) as exc:
                    failure = failure or _failure_code(exc)
                except BaseException as exc:
                    fatal = fatal or exc
            for name in ("stdout", "stderr"):
                pipe = getattr(process, name) if process is not None else None
                try:
                    raw_stream, overflow = shared._drain(pipe, LIMITS[name + "_bytes"])
                    if overflow:
                        failure = failure or "memory_" + name + "_limit"
                    elif raw_stream:
                        failure = failure or "memory_unexpected_" + name
                    _preserve(output, name + ".bin", raw_stream)
                except BaseException as exc:
                    fatal = fatal or exc
                finally:
                    if pipe is not None:
                        try:
                            pipe.close()
                        except OSError as exc:
                            failure = failure or _failure_code(exc)
            for fd in (procfd, pidfd, observerfd, retained_fd):
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError as exc:
                        failure = failure or _failure_code(exc)
        if fatal is not None:
            output.mark_failure("memory_preservation_failed" if isinstance(fatal, shared.MappingPreservationError)
                                else "memory_observation_interrupted")
            raise fatal
        capture["timing"]["finished_ns"] = time.monotonic_ns()
        capture["files"] = [{"path": name, **checker.binding(value)}
                            for name, value in sorted(output.files.items())]
        capture["failure"] = failure
        capture["status"] = "incomplete" if failure else "completed"
        capture_bytes = checker.canonical(capture)
        try:
            report = checker.verify_capture(
                selection_bytes=selection_bytes, expected_selection_sha256=expected_selection_sha256,
                capture_bytes=capture_bytes, expected_capture_sha256=checker.sha(capture_bytes), files=output.files,
            )
        except checker.MemoryCheckError as exc:
            if failure is not None:
                output.mark_failure("memory_reconstruction_rejected")
                raise
            capture["status"] = "incomplete"
            capture["failure"] = _failure_code(exc)
            capture_bytes = checker.canonical(capture)
            report = checker.verify_capture(
                selection_bytes=selection_bytes, expected_selection_sha256=expected_selection_sha256,
                capture_bytes=capture_bytes, expected_capture_sha256=checker.sha(capture_bytes), files=output.files,
            )
        output.publish(capture_bytes)
        return report
    except BaseException:
        output.mark_failure("memory_capture_not_published")
        raise
    finally:
        output.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--attempt-id", required=True)
    prepare.add_argument("--output", required=True)
    run = commands.add_parser("run-example")
    run.add_argument("--selection", required=True)
    run.add_argument("--selection-sha256", required=True)
    run.add_argument("--output-directory", required=True)
    check = commands.add_parser("check")
    check.add_argument("--selection", required=True)
    check.add_argument("--selection-sha256", required=True)
    check.add_argument("--capture-directory", required=True)
    check.add_argument("--capture-sha256", required=True)
    check.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            raw = make_selection(args.attempt_id)
            checker.write_new(args.output, raw)
            report = {"record_type": "required_gate_idempotence_memory_preparation_v0", "profile": PROFILE,
                      "status": "prepared", "selection": checker.binding(raw), **BOUNDARY}
        elif args.command == "run-example":
            report = run_example(selection_bytes=checker.read_selection_file(args.selection),
                                 expected_selection_sha256=args.selection_sha256,
                                 output_directory=args.output_directory)
        else:
            capture, files = checker.read_capture_directory(args.capture_directory)
            report = checker.verify_capture(
                selection_bytes=checker.read_selection_file(args.selection),
                expected_selection_sha256=args.selection_sha256,
                capture_bytes=capture, expected_capture_sha256=args.capture_sha256, files=files,
            )
            if args.output:
                checker.write_new(args.output, checker.canonical(report))
        sys.stdout.buffer.write(checker.canonical(report))
        return 1 if args.command == "run-example" and not report["observation_complete"] else 0
    except (OSError, ValueError, shared.MappingPreservationError) as exc:
        code = _failure_code(exc) if not isinstance(exc, shared.MappingPreservationError) else exc.code
        sys.stdout.buffer.write(checker.canonical({
            "record_type": "required_gate_idempotence_memory_command_result_v0", "profile": PROFILE,
            "status": "rejected", "error_code": code, "observation_complete": False, **BOUNDARY,
        }))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
