#!/usr/bin/env python3
"""Observe only the built-in authored probe at a cooperative stopped checkpoint.

This collector never accepts an executable, command or original runtime as an
input.  The actual executable descriptor and raw kernel records are retained;
pathname text is diagnostic only.  The kernel, procfs, CPython and its standard
library remain external trusted components.  No ptrace or privilege changes
are attempted, and the stopped probe is never resumed.
"""
from __future__ import annotations

import argparse
import errno
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
import required_gate_idempotence_mapping_probe_v0 as probe
import check_required_gate_idempotence_mapping_observation_v0 as checker

PROFILE = checker.PROFILE
BOUNDARY = checker.BOUNDARY
LIMITS = checker.LIMITS
F_ADD_SEALS, F_GET_SEALS, FULL_SEALS = 1033, 1034, 15
NAMESPACES = ("cgroup", "ipc", "mnt", "net", "pid", "user", "uts")
READ_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
DIRECTORY_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW
WAIT_FLAGS = os.WNOHANG | os.WUNTRACED | os.WCONTINUED
ENVIRONMENT = {"LC_ALL": "C", "TZ": "UTC"}


class MappingObservationError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class MappingPreservationError(RuntimeError):
    code = "mapping_preservation_failed"


def _need(condition, code):
    if not condition:
        raise MappingObservationError(code)


def _identity(info):
    return {"dev": info.st_dev, "ino": info.st_ino, "mode": info.st_mode,
            "nlink": info.st_nlink, "size": info.st_size}


def _stable_identity(info):
    return (*_identity(info).values(), info.st_mtime_ns, info.st_ctime_ns)


def _check_deadline(deadline):
    _need(time.monotonic_ns() < deadline, "mapping_wall_deadline")


def _read_fd(fd, limit, *, regular_size=False, deadline=None):
    before = os.fstat(fd)
    _need(stat.S_ISREG(before.st_mode), "mapping_file_not_regular")
    if regular_size:
        _need(0 < before.st_size <= limit, "mapping_file_size_invalid")
    data = bytearray()
    while True:
        if deadline is not None:
            _check_deadline(deadline)
        block = os.read(fd, min(65536, limit + 1 - len(data)))
        if not block:
            break
        data.extend(block)
        _need(len(data) <= limit, "mapping_file_size_limit")
    after = os.fstat(fd)
    _need(_stable_identity(before) == _stable_identity(after), "mapping_file_changed_during_read")
    if regular_size:
        _need(len(data) == before.st_size, "mapping_file_read_incomplete")
    return bytes(data)


def _open_parent(path):
    """Pin every existing ancestor; never traverse a filesystem symlink."""
    text = os.fspath(path)
    _need(type(text) is str and text and "\0" not in text
          and ".." not in Path(text).parts, "mapping_output_path_invalid")
    absolute = Path(os.path.abspath(text))
    _need(absolute.name not in {"", ".", ".."}, "mapping_output_path_invalid")
    fds, edges = [], []
    try:
        current = os.open("/", DIRECTORY_FLAGS)
        fds.append(current)
        for name in absolute.parts[1:-1]:
            child = os.open(name, DIRECTORY_FLAGS, dir_fd=current)
            info = os.fstat(child)
            linked = os.stat(name, dir_fd=current, follow_symlinks=False)
            _need((info.st_dev, info.st_ino) == (linked.st_dev, linked.st_ino),
                  "mapping_parent_changed")
            edges.append((current, name, info.st_dev, info.st_ino))
            fds.append(child)
            current = child
        return absolute, fds, edges
    except BaseException:
        for fd in reversed(fds):
            os.close(fd)
        raise


def _check_edges(edges):
    for parent, name, device, inode in edges:
        item = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _need(stat.S_ISDIR(item.st_mode) and (item.st_dev, item.st_ino) == (device, inode),
              "mapping_output_directory_changed")


def _write_exclusive(parent, name, raw):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=parent)
    try:
        original = os.fstat(fd)
        _need(stat.S_ISREG(original.st_mode) and original.st_nlink == 1
              and stat.S_IMODE(original.st_mode) == 0o600, "mapping_output_file_invalid")
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            _need(count > 0, "mapping_output_write_incomplete")
            view = view[count:]
        os.fsync(fd)
        info = os.fstat(fd)
        linked = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _need(info.st_dev == original.st_dev and info.st_ino == original.st_ino
              and _stable_identity(info) == _stable_identity(linked)
              and info.st_nlink == 1 and info.st_size == len(raw)
              and stat.S_IMODE(info.st_mode) == 0o600, "mapping_output_file_changed")
        return _stable_identity(info)
    finally:
        os.close(fd)


class _OutputDirectory:
    def __init__(self, path):
        self.path, self.fds, self.edges = _open_parent(path)
        self.files = {}
        self.identities = {}
        self.total = 0
        try:
            parent = self.fds[-1]
            os.mkdir(self.path.name, 0o700, dir_fd=parent)
            child = os.open(self.path.name, DIRECTORY_FLAGS, dir_fd=parent)
            self.fds.append(child)
            self.fd = child
            info = os.fstat(child)
            _need(stat.S_IMODE(info.st_mode) == 0o700, "mapping_output_directory_mode")
            self.root_identity = (info.st_dev, info.st_ino)
            self.edges.append((parent, self.path.name, info.st_dev, info.st_ino))
            self._check_root()
        except BaseException:
            self.close()
            raise

    def _check_root(self):
        _check_edges(self.edges)
        info = os.fstat(self.fd)
        _need(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
              and (info.st_dev, info.st_ino) == self.root_identity,
              "mapping_output_directory_changed")

    def _verify_disk(self, extra=None):
        """Reopen the original disk prefix; memory alone is not preservation."""
        expected = {name: (raw, self.identities[name]) for name, raw in self.files.items()}
        expected.update(extra or {})
        self._check_root()
        with os.scandir(self.fd) as entries:
            names = [entry.name for entry in entries]
        _need(len(names) == len(expected) and set(names) == set(expected),
              "mapping_preserved_roster_changed")
        for name, (raw, identity) in sorted(expected.items()):
            linked = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            _need(_stable_identity(linked) == identity and stat.S_ISREG(linked.st_mode)
                  and linked.st_nlink == 1 and stat.S_IMODE(linked.st_mode) == 0o600,
                  "mapping_preserved_identity_changed")
            fd = os.open(name, READ_FLAGS, dir_fd=self.fd)
            try:
                _need(_stable_identity(os.fstat(fd)) == identity, "mapping_preserved_identity_changed")
                observed = _read_fd(fd, len(raw))
                _need(observed == raw and _stable_identity(os.fstat(fd)) == identity,
                      "mapping_preserved_bytes_changed")
                _need(_stable_identity(os.stat(name, dir_fd=self.fd, follow_symlinks=False)) == identity,
                      "mapping_preserved_identity_changed")
            finally:
                os.close(fd)
        # A later file read may race with replacement or modification of an
        # earlier file.  Recheck the entire original prefix at this boundary.
        with os.scandir(self.fd) as entries:
            names = [entry.name for entry in entries]
        _need(len(names) == len(expected) and set(names) == set(expected),
              "mapping_preserved_roster_changed")
        for name, (_, identity) in sorted(expected.items()):
            _need(_stable_identity(os.stat(name, dir_fd=self.fd, follow_symlinks=False)) == identity,
                  "mapping_preserved_identity_changed")
        self._check_root()

    def preserve(self, name, raw):
        try:
            _need(name in checker.FILE_NAMES and name not in self.files
                  and type(raw) is bytes, "mapping_preservation_roster")
            _need(self.total + len(raw) <= LIMITS["total_capture_bytes"], "mapping_capture_size_limit")
            self._check_root()
            identity = _write_exclusive(self.fd, name, raw)
            self._check_root()
            self.files[name] = raw
            self.identities[name] = identity
            self.total += len(raw)
        except (OSError, ValueError) as exc:
            raise MappingPreservationError("mapping_preservation_failed") from exc

    def publish(self, raw):
        try:
            self._verify_disk()
            identity = _write_exclusive(self.fd, "capture.json", raw)
            os.fsync(self.fd)
            self._verify_disk({"capture.json": (raw, identity)})
        except (OSError, ValueError) as exc:
            raise MappingPreservationError("mapping_preservation_failed") from exc

    def mark_failure(self, code):
        try:
            self._check_root()
            raw = checker.canonical({"record_type": "required_gate_idempotence_mapping_failure_v0",
                                     "profile": PROFILE, "status": "incomplete", "failure": code,
                                     **BOUNDARY})
            _write_exclusive(self.fd, "attempt.incomplete.json", raw)
            os.fsync(self.fd)
        except (OSError, ValueError):
            pass  # No accepted capture is published if preservation fails.

    def close(self):
        for fd in reversed(self.fds):
            os.close(fd)
        self.fds = []


def _preserve(output, name, raw):
    output.preserve(name, raw)


def _actual_observer():
    _need(sys.platform == "linux" and os.uname().machine == "x86_64",
          "mapping_platform_unsupported")
    path = os.readlink("/proc/self/exe")
    _need(path.startswith("/") and len(path) <= 4096 and "\0" not in path
          and not path.endswith(" (deleted)"), "mapping_observer_path_invalid")
    fd = os.open("/proc/self/exe", os.O_RDONLY | os.O_CLOEXEC)
    try:
        raw = _read_fd(fd, LIMITS["observer_executable_bytes"], regular_size=True)
        _need(os.readlink("/proc/self/exe") == path, "mapping_observer_changed")
        return {"path": path, **checker.binding(raw)}, raw
    finally:
        os.close(fd)


def make_selection(attempt_id):
    _need(type(attempt_id) is str and re.fullmatch(r"[0-9a-f]{32}", attempt_id) is not None,
          "mapping_attempt_id_invalid")
    observer, _ = _actual_observer()
    raw = checker.canonical({
        "record_type": "required_gate_idempotence_mapping_selection_v0", "profile": PROFILE,
        "attempt_id": attempt_id, "probe": checker.binding(probe.probe_bytes()),
        "observer": observer, "sources": checker.source_bindings(), "limits": dict(LIMITS), **BOUNDARY,
    })
    checker.validate_selection(raw, checker.sha(raw))
    return raw


def _sealed_probe(raw):
    fd = os.memfd_create("pulse-mapping-probe-v0", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            _need(count > 0, "mapping_probe_write_incomplete")
            view = view[count:]
        os.fchmod(fd, 0o500)
        fcntl.fcntl(fd, F_ADD_SEALS, FULL_SEALS)
        _need(fcntl.fcntl(fd, F_GET_SEALS) == FULL_SEALS, "mapping_probe_seal_mismatch")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _spawn_probe(fd, parent_pid):
    return subprocess.Popen(
        ["pulse-mapping-probe-v0", probe.parent_argument(parent_pid)],
        executable="/proc/self/fd/" + str(fd), stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
        pass_fds=(fd,), env=dict(ENVIRONMENT), cwd="/", start_new_session=True,
    )


def _read_proc(proc_fd, name, limit):
    fd = os.open(name, READ_FLAGS, dir_fd=proc_fd)
    try:
        return _read_fd(fd, limit)
    finally:
        os.close(fd)


def _read_executable(proc_fd):
    # This fixed procfs magic link intentionally opens the actual executable.
    # It never resolves the displayed pathname or uses map_files as a fallback.
    fd = os.open("exe", os.O_RDONLY | os.O_CLOEXEC, dir_fd=proc_fd)
    try:
        info = os.fstat(fd)
        seals = fcntl.fcntl(fd, F_GET_SEALS)
        raw = _read_fd(fd, probe.PAGE_BYTES, regular_size=True)
        _need(_stable_identity(info) == _stable_identity(os.fstat(fd))
              and seals == fcntl.fcntl(fd, F_GET_SEALS), "mapping_executable_changed")
        return {"stat": _identity(info), "seals": seals}, raw
    finally:
        os.close(fd)


def _namespaces(proc_fd):
    result = {}
    for name in NAMESPACES:
        value = os.readlink("ns/" + name, dir_fd=proc_fd)
        _need(len(value) <= 128, "mapping_namespace_size_limit")
        result[name] = value
    return result


def _drain(pipe, limit):
    result = bytearray()
    overflow = False
    if pipe is None:
        return b"", False
    os.set_blocking(pipe.fileno(), False)
    while True:
        try:
            block = os.read(pipe.fileno(), min(65536, limit + 1 - len(result)))
        except BlockingIOError:
            break
        if not block:
            break
        available = limit - len(result)
        result.extend(block[:available])
        if len(block) > available:
            overflow = True
            break
    return bytes(result), overflow


def _terminal(capture, process, status):
    if os.WIFEXITED(status) or os.WIFSIGNALED(status):
        capture["wait"]["terminal"] = status
        capture["ownership"]["child_reaped"] = True
        process.returncode = os.waitstatus_to_exitcode(status)
        return True
    return False


def _cleanup(process, pidfd, capture, wall_deadline):
    if process is None or capture["ownership"]["child_reaped"]:
        return None
    # Even an overdue failed read must receive a bounded opportunity to reap
    # our child.  Completed observations separately satisfy the total budget.
    deadline = time.monotonic_ns() + LIMITS["cleanup_seconds"] * 10**9
    failure = None
    try:
        if pidfd is not None:
            signal.pidfd_send_signal(pidfd, signal.SIGKILL)
        else:
            # The unreaped direct child cannot have its PID reused.  This is
            # cleanup after pidfd acquisition failure, never completed evidence.
            os.kill(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError:
        failure = "mapping_cleanup_pidfd_signal_failed"
        # A failed preferred signaling API must not strand our stopped child.
        # The unreaped owned PID is still unambiguous.  This cleanup backstop
        # never qualifies an observation as completed.
        try:
            os.kill(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            return "mapping_cleanup_signal_failed"
    while time.monotonic_ns() < deadline:
        try:
            got, status = os.waitpid(process.pid, WAIT_FLAGS)
        except InterruptedError:
            continue
        except ChildProcessError:
            process.returncode = -255
            return "mapping_cleanup_wait_unavailable"
        except OSError:
            return "mapping_cleanup_wait_failed"
        if got and _terminal(capture, process, status):
            return failure
        time.sleep(0.002)
    return "mapping_cleanup_deadline"


def run_example(*, selection_bytes, expected_selection_sha256, output_directory):
    selection = checker.validate_selection(selection_bytes, expected_selection_sha256)
    observer, observer_bytes = _actual_observer()
    _need(observer == selection["observer"], "mapping_observer_selection_mismatch")
    _need(hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal")
          and hasattr(os, "memfd_create"), "mapping_host_api_unsupported")
    output = _OutputDirectory(output_directory)
    started = time.monotonic_ns()
    wall_deadline = started + LIMITS["wall_seconds"] * 10**9
    parent_pid = os.getpid()
    capture = {
        "record_type": "required_gate_idempotence_mapping_capture_v0", "profile": PROFILE,
        "attempt_id": selection["attempt_id"], "selection_sha256": expected_selection_sha256,
        "status": "incomplete", "failure": None, "observer_pid": parent_pid, "child_pid": None,
        "timing": {"started_ns": started, "stopped_ns": None, "finished_ns": None},
        "wait": {"initial": None, "observation": None, "terminal": None},
        "ownership": {"pidfd_opened": False, "proc_dir_pinned": False,
                      "child_reaped": False, "resumed_after_stop": False},
        "objects": {"retained": None, "executable": None}, "files": [], **BOUNDARY,
    }
    process = None
    pidfd = procfd = observerfd = retained_fd = None
    failure = None
    fatal = None
    try:
        try:
            _preserve(output, "selection.json", selection_bytes)
            _preserve(output, "attempt_start.json", checker.canonical({
                "record_type": "required_gate_idempotence_mapping_attempt_start_v0", "profile": PROFILE,
                "attempt_id": selection["attempt_id"], "selection_sha256": expected_selection_sha256,
                "observer_pid": parent_pid, "started_ns": started,
            }))
            raw = probe.probe_bytes()
            _preserve(output, "probe.elf", raw)
            _preserve(output, "observer.exe.bin", observer_bytes)
            observerfd = os.open("/proc/self", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            for name in ("stat", "status"):
                _preserve(output, "observer." + name + ".bin",
                          _read_proc(observerfd, name, LIMITS["proc_file_bytes"]))
            bootfd = os.open("/proc/sys/kernel/random/boot_id", READ_FLAGS)
            try:
                _preserve(output, "kernel.boot_id.bin", _read_fd(bootfd, 128))
            finally:
                os.close(bootfd)
            retained_fd = _sealed_probe(raw)
            capture["objects"]["retained"] = {
                "stat": _identity(os.fstat(retained_fd)), "seals": fcntl.fcntl(retained_fd, F_GET_SEALS),
            }
            _preserve(output, "retained.elf", _read_fd(retained_fd, probe.PAGE_BYTES, regular_size=True))
            _check_deadline(wall_deadline)
            process = _spawn_probe(retained_fd, parent_pid)
            capture["child_pid"] = process.pid
            pidfd = os.pidfd_open(process.pid, 0)
            capture["ownership"]["pidfd_opened"] = True
            procfd = os.open("/proc/" + str(process.pid), DIRECTORY_FLAGS)
            capture["ownership"]["proc_dir_pinned"] = True
            while True:
                _check_deadline(wall_deadline)
                got, status = os.waitpid(process.pid, WAIT_FLAGS)
                if not got:
                    time.sleep(0.002)
                    continue
                capture["wait"]["initial"] = status
                _terminal(capture, process, status)
                _need(os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGSTOP,
                      "mapping_expected_stop_missing")
                capture["timing"]["stopped_ns"] = time.monotonic_ns()
                break
            for name in ("stat", "status", "maps"):
                _check_deadline(wall_deadline)
                _preserve(output, "child." + name + ".before.bin",
                          _read_proc(procfd, name, LIMITS["proc_file_bytes"]))
            infofd = os.open("/proc/self/fdinfo/" + str(pidfd), READ_FLAGS)
            try:
                _preserve(output, "child.pidfd.info.bin", _read_fd(infofd, LIMITS["proc_file_bytes"]))
            finally:
                os.close(infofd)
            link = os.readlink("exe", dir_fd=procfd).encode("utf-8")
            _need(len(link) <= LIMITS["proc_file_bytes"], "mapping_executable_link_limit")
            _preserve(output, "child.exe.link.bin", link)
            capture["objects"]["executable"], executable_raw = _read_executable(procfd)
            _preserve(output, "executable.elf", executable_raw)
            _need(capture["objects"]["executable"] == capture["objects"]["retained"]
                  and executable_raw == raw, "mapping_executable_object_mismatch")
            system = os.uname()
            host = {"platform": {"system": system.sysname, "machine": system.machine,
                                 "release": system.release, "version": system.version},
                    "observer_namespaces": _namespaces(observerfd), "child_namespaces": _namespaces(procfd)}
            _preserve(output, "host.json", checker.canonical(host))
            for name in ("maps", "status", "stat"):
                _check_deadline(wall_deadline)
                _preserve(output, "child." + name + ".after.bin",
                          _read_proc(procfd, name, LIMITS["proc_file_bytes"]))
            _need(output.files["child.maps.before.bin"] == output.files["child.maps.after.bin"],
                  "mapping_checkpoint_maps_changed")
            _check_deadline(wall_deadline)
            got, status = os.waitpid(process.pid, WAIT_FLAGS)
            if got:
                capture["wait"]["observation"] = status
                _terminal(capture, process, status)
            _need(not got, "mapping_checkpoint_wait_changed")
        except MappingPreservationError as exc:
            fatal = exc
        except (OSError, ValueError) as exc:
            failure = (exc.code if isinstance(exc, MappingObservationError)
                       else "mapping_os_error_" + str(exc.errno) if isinstance(exc, OSError)
                       else "mapping_observation_invalid")
        except BaseException as exc:
            fatal = exc
        finally:
            cleanup_failure = _cleanup(process, pidfd, capture, wall_deadline)
            failure = cleanup_failure or failure
            for name in ("stdout", "stderr"):
                pipe = getattr(process, name) if process is not None else None
                try:
                    raw_stream, overflow = _drain(pipe, LIMITS[name + "_bytes"])
                    if overflow:
                        failure = failure or "mapping_" + name + "_limit"
                    _preserve(output, name + ".bin", raw_stream)
                except BaseException as exc:
                    fatal = fatal or exc
                finally:
                    if pipe is not None:
                        pipe.close()
            for fd in (procfd, pidfd, observerfd, retained_fd):
                if fd is not None:
                    os.close(fd)
        if fatal is not None:
            output.mark_failure("mapping_preservation_failed" if isinstance(fatal, MappingPreservationError)
                                else "mapping_observation_interrupted")
            raise fatal
        capture["timing"]["finished_ns"] = time.monotonic_ns()
        capture["files"] = [{"path": name, **checker.binding(raw)} for name, raw in sorted(output.files.items())]
        capture["failure"] = failure
        capture["status"] = "incomplete" if failure else "completed"
        capture_bytes = checker.canonical(capture)
        try:
            report = checker.verify_capture(
                selection_bytes=selection_bytes, expected_selection_sha256=expected_selection_sha256,
                capture_bytes=capture_bytes, expected_capture_sha256=checker.sha(capture_bytes), files=output.files,
            )
        except checker.MappingError as exc:
            if failure is not None:
                output.mark_failure("mapping_reconstruction_rejected")
                raise
            # A failed live relation is preserved as incomplete.  Selection,
            # sources and manifest are still independently checked again.
            capture["status"] = "incomplete"
            code = str(exc)
            capture["failure"] = code if re.fullmatch(r"[a-z][a-z0-9_]*", code) else "mapping_reconstruction_rejected"
            capture_bytes = checker.canonical(capture)
            report = checker.verify_capture(
                selection_bytes=selection_bytes, expected_selection_sha256=expected_selection_sha256,
                capture_bytes=capture_bytes, expected_capture_sha256=checker.sha(capture_bytes), files=output.files,
            )
        output.publish(capture_bytes)
        return report
    except BaseException:
        output.mark_failure("mapping_capture_not_published")
        raise
    finally:
        output.close()


def _input(path, limit=1024 * 1024):
    absolute, fds, edges = _open_parent(path)
    try:
        fd = os.open(absolute.name, READ_FLAGS, dir_fd=fds[-1])
        try:
            _need(os.fstat(fd).st_nlink == 1, "mapping_input_hardlink")
            raw = _read_fd(fd, limit, regular_size=True)
            _check_edges(edges)
            return raw
        finally:
            os.close(fd)
    finally:
        for fd in reversed(fds):
            os.close(fd)


def _publish_new_file(path, raw):
    absolute, fds, edges = _open_parent(path)
    try:
        _check_edges(edges)
        _write_exclusive(fds[-1], absolute.name, raw)
        os.fsync(fds[-1])
        _check_edges(edges)
    finally:
        for fd in reversed(fds):
            os.close(fd)


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
            _publish_new_file(args.output, raw)
            report = {"record_type": "required_gate_idempotence_mapping_preparation_v0", "profile": PROFILE,
                      "status": "prepared", "selection": checker.binding(raw), **BOUNDARY}
        elif args.command == "run-example":
            report = run_example(selection_bytes=_input(args.selection),
                                 expected_selection_sha256=args.selection_sha256,
                                 output_directory=args.output_directory)
        else:
            capture, files = checker.read_capture_directory(args.capture_directory)
            report = checker.verify_capture(
                selection_bytes=_input(args.selection), expected_selection_sha256=args.selection_sha256,
                capture_bytes=capture, expected_capture_sha256=args.capture_sha256, files=files,
            )
            if args.output:
                _publish_new_file(args.output, checker.canonical(report))
        sys.stdout.buffer.write(checker.canonical(report))
        return 1 if args.command == "run-example" and not report["observation_complete"] else 0
    except (OSError, ValueError, MappingPreservationError) as exc:
        code = str(exc) if isinstance(exc, checker.MappingError) else getattr(exc, "code", "mapping_command_failed")
        sys.stdout.buffer.write(checker.canonical({
            "record_type": "required_gate_idempotence_mapping_command_result_v0", "profile": PROFILE,
            "status": "rejected", "error_code": code, "observation_complete": False, **BOUNDARY,
        }))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
